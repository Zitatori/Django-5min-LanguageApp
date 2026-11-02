from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from core.models import TutorProfile


class TutorAccessTests(TestCase):
    def test_student_cannot_open_or_activate_dashboard(self):
        user = User.objects.create_user('student-access')
        self.client.force_login(user)
        url = reverse('tutor_dashboard')
        for response in (self.client.get(url), self.client.post(url, {'action': 'go_online'})):
            self.assertEqual(response.status_code, 403)
        self.assertFalse(TutorProfile.objects.filter(user=user).exists())
        self.assertNotContains(self.client.get('/'), 'href="%s"' % url)

    def test_tutor_and_admin_can_open_dashboard_and_see_navigation(self):
        for staff in (False, True):
            user = User.objects.create_user('access-%s' % staff, is_staff=staff)
            if not staff:
                TutorProfile.objects.create(user=user)
            self.client.force_login(user)
            url = reverse('tutor_dashboard')
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertContains(self.client.get('/'), 'href="%s"' % url, count=3)

    def test_anonymous_is_sent_to_login(self):
        self.assertEqual(self.client.get(reverse('tutor_dashboard')).status_code, 302)
