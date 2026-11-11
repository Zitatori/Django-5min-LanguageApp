from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.utils import translation
from core.services.pricing import display_currency, price_label, rate_for
from core.models import StudentProfile, PointBalance


class DisplayCurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('currency-test')
        StudentProfile.objects.create(user=self.user)
        PointBalance.objects.create(user=self.user, student_balance=2)
        self.client.force_login(self.user)

    def test_default_and_cookie_independent_of_language(self):
        request = RequestFactory().get('/')
        request.LANGUAGE_CODE = 'ja'
        self.assertEqual(display_currency(request), 'JPY')
        request.COOKIES['display_currency'] = 'EUR'
        self.assertEqual(display_currency(request), 'EUR')
        request.LANGUAGE_CODE = 'fr'
        self.assertEqual(display_currency(request), 'EUR')
        request.COOKIES['display_currency'] = 'invalid'
        self.assertEqual(display_currency(request), 'CHF')

    def test_fixed_prices(self):
        with translation.override('en'):
            for currency, expected in [('JPY', 'JPY 19,000'), ('CHF', 'CHF 100.00'), ('USD', 'USD 120.00'), ('EUR', 'EUR 110.00')]:
                self.assertEqual(price_label(100, currency), expected)

    @override_settings(DISPLAY_CURRENCY_RATES={'USD': 'NaN', 'EUR': '-1'})
    def test_invalid_rate_fallback(self):
        self.assertEqual(str(rate_for('USD')), '1.2')
        self.assertEqual(str(rate_for('EUR')), '1.1')

    def test_selection_persists_on_both_pages_and_keeps_balance(self):
        response = self.client.post(reverse('set_display_currency'), {'currency': 'EUR', 'next': reverse('purchase_points')})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies['display_currency'].value, 'EUR')
        for language in ['ja', 'en', 'fr', 'es']:
            self.client.cookies['django_language'] = language
            for name in ['purchase_points', 'profile']:
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'value="EUR" selected')
                self.assertNotContains(response, 'CHF 100 /')
        self.assertEqual(PointBalance.objects.get(user=self.user).student_balance, 2)

    def test_invalid_currency_and_external_redirect(self):
        url = reverse('set_display_currency')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'currency': 'BAD'}).status_code, 400)
        response = self.client.post(url, {'currency': 'USD', 'next': 'https://example.com'})
        self.assertEqual(response.url, reverse('profile'))
