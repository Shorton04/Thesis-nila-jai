# tests/test_accounts.py
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from accounts.models import CustomUser, UserProfile, LoginHistory
from accounts.forms import CustomUserCreationForm


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.profile_url = reverse('accounts:profile')

        # Test user data
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'phone_number': '1234567890',
            'company_name': 'Test Company',
            'position': 'Manager',
            'business_type': 'Testing'
        }

    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_register_view_post_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # Verify that one email was sent
        self.assertIn('verify your email', mail.outbox[0].subject.lower())

    def test_register_view_post_invalid_data(self):
        # Test with invalid email
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_success(self):
        # Create a verified user
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_email_verified=True
        )

        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'remember_me': True
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful login
        self.assertTrue(LoginHistory.objects.filter(user=user, is_successful=True).exists())

    def test_login_unverified_email(self):
        # Create an unverified user
        CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_email_verified=False
        )

        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'verify your email')

    def test_profile_view(self):
        # Create and login a user
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_email_verified=True
        )
        self.client.login(username='testuser', password='TestPass123!')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')