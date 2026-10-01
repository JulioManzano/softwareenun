"""Firebase is the identity authority for cloud tools; email is profile data."""
from functools import wraps
from threading import Lock
import uuid

import firebase_admin
from firebase_admin import auth
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from graphql import GraphQLError

_app_lock = Lock()


class FirebaseAuthenticationError(Exception):
    pass


def firebase_app():
    with _app_lock:
        try:
            return firebase_admin.get_app("multitools")
        except ValueError:
            if not settings.FIREBASE_PROJECT_ID:
                raise FirebaseAuthenticationError("Firebase no está configurado.")
            return firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}, name="multitools"
            )


def authenticate_request(request):
    request.firebase_claims = None
    header = request.headers.get("Authorization", "")
    if not header:
        return
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise FirebaseAuthenticationError("Autenticación inválida.")
    try:
        claims = auth.verify_id_token(parts[1], app=firebase_app(), check_revoked=True)
    except Exception as exc:
        # SDK errors may contain credentials/token details; never expose them.
        raise FirebaseAuthenticationError("La sesión no es válida o expiró.") from exc
    uid = claims.get("uid")
    if not isinstance(uid, str) or not uid or len(uid) > 128:
        raise FirebaseAuthenticationError("Identidad inválida.")
    email = claims.get("email") or None
    if email:
        try:
            validate_email(email)
        except ValidationError:
            email = None
        if email and len(email) > 254:
            email = None
    User = get_user_model()
    # UID uniqueness and get_or_create handle concurrent first requests.
    with transaction.atomic():
        user, created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={
                "username": f"firebase_{uuid.uuid4().hex}",
                "email": email,
                "email_verified": claims.get("email_verified") is True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
    if not user.is_active or user.is_banned or user.is_deleted:
        raise FirebaseAuthenticationError("Esta cuenta no tiene acceso.")
    request.user = user
    request.firebase_claims = claims


def firebase_required(resolver):
    """Apply to every cloud resolver; ownership must use info.context.user."""
    @wraps(resolver)
    def wrapped(root, info, *args, **kwargs):
        user = info.context.user
        if not getattr(info.context, "firebase_claims", None) or not user.is_authenticated:
            raise GraphQLError("Iniciá sesión para continuar.", extensions={"code": "UNAUTHENTICATED"})
        if not user.is_active or user.is_banned or user.is_deleted:
            raise GraphQLError("Esta cuenta no tiene acceso.", extensions={"code": "FORBIDDEN"})
        return resolver(root, info, *args, **kwargs)
    return wrapped
