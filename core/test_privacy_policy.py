from django.test import TestCase
from django.urls import reverse


class MultiToolsPrivacyPolicyTests(TestCase):
    def test_policy_is_public_and_describes_app_data_handling(self):
        response = self.client.get(reverse("multitools-privacy-policy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Política de privacidad")
        self.assertContains(response, "Mejorar imagen")
        self.assertContains(response, "archivos públicos")
        self.assertContains(response, "Replicate")
