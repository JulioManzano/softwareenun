from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory, override_settings

from config.urls import schema
from core.models import User
from core.services.firebase_auth import authenticate_request, FirebaseAuthenticationError


@override_settings(ALLOWED_HOSTS=["testserver"])
class FirebaseAuthTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.app_patch = patch("core.services.firebase_auth.firebase_app", return_value=object())
        self.app_patch.start()
        self.addCleanup(self.app_patch.stop)

    def request(self, token=None):
        request = self.factory.post("/graphql/", HTTP_AUTHORIZATION=token or "")
        request.user = AnonymousUser()
        return request

    def authenticate(self, claims):
        request = self.request("Bearer firebase-token")
        with patch("core.services.firebase_auth.auth.verify_id_token", return_value=claims) as verify:
            authenticate_request(request)
            self.assertTrue(verify.call_args.kwargs["check_revoked"])
        return request

    def test_provision_and_reuse_uid_with_unusable_password(self):
        request = self.authenticate({"uid": "uid-one", "email": "a@example.com", "email_verified": True})
        self.assertFalse(request.user.has_usable_password())
        self.assertTrue(request.user.email_verified)
        again = self.authenticate({"uid": "uid-one", "email": "changed@example.com"})
        self.assertEqual(again.user.pk, request.user.pk)
        self.assertEqual(User.objects.count(), 1)
        result = schema.execute("{ me { firebase_uid email } }", context_value=request)
        self.assertIsNone(result.errors)
        self.assertEqual(result.data["me"]["firebase_uid"], "uid-one")

    def test_same_email_does_not_link_existing_or_other_firebase_accounts(self):
        existing = User.objects.create_user(username="existing", email="a@example.com")
        first = self.authenticate({"uid": "one", "email": existing.email})
        second = self.authenticate({"uid": "two", "email": existing.email})
        self.assertNotEqual(first.user.pk, existing.pk)
        self.assertNotEqual(first.user.pk, second.user.pk)
        existing.refresh_from_db()
        self.assertIsNone(existing.firebase_uid)

    def test_multiple_accounts_without_email(self):
        one = self.authenticate({"uid": "one"})
        two = self.authenticate({"uid": "two"})
        self.assertIsNone(one.user.email)
        self.assertNotEqual(one.user.username, two.user.username)

    def test_invalid_token_never_creates_user_or_exposes_sdk_error(self):
        with patch("core.services.firebase_auth.auth.verify_id_token", side_effect=ValueError("SECRET")):
            response = self.client.post("/graphql/", {"query": "{ me { id } }"}, content_type="application/json", HTTP_AUTHORIZATION="Bearer invalid")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("SECRET", response.content.decode())
        self.assertEqual(User.objects.count(), 0)

    def test_malformed_authorization_rejected(self):
        for header in ("Bearer", "Basic abc", "Bearer a b"):
            with self.subTest(header=header), self.assertRaises(FirebaseAuthenticationError):
                authenticate_request(self.request(header))

    def test_invalid_uid_rejected(self):
        for uid in (None, "", "x" * 129):
            with self.subTest(uid=uid), self.assertRaises(FirebaseAuthenticationError):
                self.authenticate({"uid": uid})
        self.assertEqual(User.objects.count(), 0)

    def test_inactive_banned_deleted_users_rejected(self):
        for field in ("is_active", "is_banned", "is_deleted"):
            user = User.objects.create_user(username=field, firebase_uid=field)
            setattr(user, field, field != "is_active")
            user.save()
            with self.subTest(field=field), self.assertRaises(FirebaseAuthenticationError):
                self.authenticate({"uid": field})

    def test_public_queries_remain_anonymous_and_me_requires_firebase(self):
        request = self.request()
        authenticate_request(request)
        public = schema.execute("{ public_files { id } }", context_value=request)
        self.assertIsNone(public.errors)
        protected = schema.execute("{ me { id } }", context_value=request)
        self.assertEqual(protected.errors[0].extensions["code"], "UNAUTHENTICATED")
        request.user = User.objects.create_user(username="django-session")
        protected = schema.execute("{ me { id } }", context_value=request)
        self.assertEqual(protected.errors[0].extensions["code"], "UNAUTHENTICATED")

    def test_graphql_http_authenticates_bearer_token(self):
        with patch("core.services.firebase_auth.auth.verify_id_token", return_value={"uid": "http-user"}):
            response = self.client.post(
                "/graphql/", {"query": "{ me { firebase_uid } }"},
                content_type="application/json", HTTP_AUTHORIZATION="Bearer firebase-token",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["me"]["firebase_uid"], "http-user")

    def test_web_authorization_preflight_is_allowed_without_session(self):
        response = self.client.options(
            "/graphql/", HTTP_ORIGIN="https://multitools.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("authorization", response["Access-Control-Allow-Headers"])
        self.assertEqual(User.objects.count(), 0)
