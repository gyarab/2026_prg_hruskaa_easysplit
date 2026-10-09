from django.test import TestCase
from django.urls import reverse

from .models import User


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("register")
        self.data = {
            "username": "novak",
            "email": "novak@example.com",
            "first_name": "Jan",
            "last_name": "Novák",
            "password1": "SilneHeslo-12345",
            "password2": "SilneHeslo-12345",
        }

    def test_register_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_successful_registration_logs_user_in(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="novak").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_password_is_hashed(self):
        self.client.post(self.url, self.data)
        user = User.objects.get(username="novak")
        self.assertNotEqual(user.password, self.data["password1"])
        self.assertTrue(user.check_password(self.data["password1"]))

    def test_duplicate_email_rejected(self):
        User.objects.create_user("jiny", "novak@example.com", "x")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="novak").exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("novak", "novak@example.com", "SilneHeslo-12345")

    def test_login(self):
        response = self.client.post(
            reverse("login"), {"username": "novak", "password": "SilneHeslo-12345"}
        )
        self.assertRedirects(response, reverse("home"))

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"username": "novak", "password": "spatne"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_logs_out(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)