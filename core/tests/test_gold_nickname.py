from urllib.parse import parse_qs, urlparse
from django.contrib.auth.models import User
from django.core import signing
from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class GoldNicknameTests(TestCase):
    def test_nickname_mail_and_stable_referral_in_all_languages(self):
        user = User.objects.create_user('member_' + 'a' * 32, first_name='マリア & Marie', email='maria@example.com')
        self.client.force_login(user)
        for language in ('ja', 'en', 'fr', 'es'):
            with self.subTest(language=language), translation.override(language):
                response = self.client.get(reverse('profile'), HTTP_ACCEPT_LANGUAGE=language)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['gold_nickname'], user.first_name)
                body = parse_qs(urlparse(response.context['gold_mailto']).query)['body'][0]
                self.assertIn(user.first_name, body)
                self.assertIn(user.email, body)
                self.assertNotIn(user.username, body)
                token = parse_qs(urlparse(response.context['referral_link']).query)['ref'][0]
                self.assertEqual(signing.loads(token, salt='referral-link'), user.pk)
                self.assertContains(response, 'id="copy-referral"')
                self.assertNotContains(response, user.username)
