from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile

class UserRoleTests(TestCase):
    def test_new_web_user_is_consumer(self):
        user = User.objects.create_user(username="consumer", password="password123")
        self.assertEqual(user.profile.role, UserProfile.Role.CONSUMER)

    def test_consumer_cannot_access_merchant_dashboard(self):
        user = User.objects.create_user(username="consumer", password="password123")
        self.client.force_login(user)
        response = self.client.get(reverse("main:product_view"))
        self.assertRedirects(response, reverse("main:show_main"))

    def test_merchant_can_access_merchant_dashboard(self):
        user = User.objects.create_user(username="merchant", password="password123")
        user.profile.role = UserProfile.Role.MERCHANT
        user.profile.save()
        self.client.force_login(user)
        response = self.client.get(reverse("main:product_view"))
        self.assertEqual(response.status_code, 200)
