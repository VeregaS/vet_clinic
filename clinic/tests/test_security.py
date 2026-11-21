from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    SECURITY_POST_LIMITS={"login": (2, 300), "booking": (2, 300)},
    TRUST_PROXY_HEADERS=False,
)
class RequestSecurityTests(TestCase):
    def setUp(self):
        self.enterContext(patch("clinic.security.time", return_value=1900))

    def test_staff_and_admin_login_share_limit_and_ignore_forwarded_ip(self):
        data = {"username": "demo", "password": "invalid"}
        self.assertEqual(self.client.post(reverse("login"), data).status_code, 200)
        self.assertEqual(
            self.client.post(reverse("admin:login"), data).status_code, 200
        )
        response = self.client.post(reverse("login"), data, HTTP_X_REAL_IP="192.0.2.54")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(
            self.client.post(
                reverse("login"), data, REMOTE_ADDR="192.0.2.55"
            ).status_code,
            200,
        )

    def test_booking_has_separate_limit(self):
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("home"), {}).status_code, 200)
        self.assertEqual(self.client.post(reverse("home"), {}).status_code, 429)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_public_page_has_browser_security_headers(self):
        response = self.client.get(reverse("home"))
        self.assertIn("object-src 'none'", response["Content-Security-Policy"])
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_booking_rejects_a_filled_honeypot(self):
        response = self.client.post(reverse("home"), {"company_website": "filled"})
        self.assertTrue(response.context["form"].has_error("company_website"))
