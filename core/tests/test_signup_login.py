from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from core.forms import SignupForm


class SignupLoginTests(TestCase):
    def setUp(self):
        self.data = dict(learning_languages=['ja', 'fr'], email='new@example.com', display_name='Maria', password1='Valid!Pass8492', password2='Valid!Pass8492')

    def test_signup_without_username(self):
        self.assertNotIn('username', SignupForm().fields)
        response = self.client.post(reverse('signup'), self.data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email=self.data['email'])
        self.assertEqual(user.first_name, 'Maria')
        self.assertTrue(user.username)
        self.assertEqual(set(user.studentprofile.learning_languages.values_list('code', flat=True)), {'ja', 'fr'})
        self.assertEqual(user.point_balance.student_balance, 2)
        self.client.logout()
        response = self.client.post(reverse('login'), {'username': 'NEW@example.com', 'password': self.data['password1']})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_required_fields_and_duplicate_email(self):
        for field in ['email', 'display_name', 'learning_languages']:
            form = SignupForm({**self.data, field: ' '})
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)
        User.objects.create_user(username='legacy', email='NEW@example.com')
        form = SignupForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_legacy_username_and_email_and_inactive(self):
        user = User.objects.create_user(username='legacy', email='old@example.com', password=self.data['password1'])
        for identifier in ['legacy', 'OLD@example.com']:
            self.assertEqual(authenticate(username=identifier, password=self.data['password1']), user)
        self.assertIsNone(authenticate(username='legacy', password='wrong'))
        User.objects.create_user(username='other', email='old@example.com')
        self.assertIsNone(authenticate(username='old@example.com', password=self.data['password1']))
        self.assertEqual(authenticate(username='legacy', password=self.data['password1']), user)
        user.is_active = False
        user.save()
        self.assertIsNone(authenticate(username='legacy', password=self.data['password1']))

    def test_invalid_learning_language_does_not_create_user(self):
        response = self.client.post(reverse('signup'), {**self.data, 'learning_languages': ['unknown']})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email=self.data['email']).exists())
