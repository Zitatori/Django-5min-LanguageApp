from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PaymentDetailsTests(TestCase):
    def test_both_purchase_pages_show_payment_details_in_four_languages(self):
        self.client.force_login(User.objects.create_user('payment-test', first_name='Maria'))
        for language in ('ja', 'en', 'fr', 'es'):
            for name in ('profile', 'purchase_points'):
                with self.subTest(language=language, name=name):
                    response = self.client.get(reverse(name), HTTP_ACCEPT_LANGUAGE=language)
                    for value in ('0307779', '661', 'ディトメイヤー美鈴', 'zitatori@gmail.com', '0766172728'):
                        self.assertContains(response, value)
                    self.assertContains(response, '24')
                    self.assertContains(response, '3')
