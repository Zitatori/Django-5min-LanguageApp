from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import StudentProfile, UpcomingSession

class AttendanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('student')
        self.student = StudentProfile.objects.create(user=self.user)
        self.session = UpcomingSession.objects.create(start_time=timezone.now()+timedelta(hours=1), end_time=timezone.now()+timedelta(hours=2), is_published=True)
        self.url = reverse('session_attendance', args=[self.session.pk])
        self.client.force_login(self.user)

    def test_add_idempotent_cancel_only_own_and_home(self):
        other = StudentProfile.objects.create(user=User.objects.create_user('other'))
        self.session.planned_students.add(other)
        for _ in range(2):
            self.assertEqual(self.client.post(self.url, {'attending':'yes'}).status_code,302)
        self.assertEqual(self.session.planned_students.count(),2)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'aria-pressed="true"')
        self.assertTrue(response.context['next_session']['obj'].is_planned)
        self.assertEqual(self.client.post(self.url, {'attending':'no'}).status_code,302)
        self.assertEqual(list(self.session.planned_students.all()),[other])

    def test_auth_method_and_visibility(self):
        self.assertEqual(self.client.get(self.url).status_code,405)
        self.assertEqual(self.client.post(self.url, {'attending':'bad'}).status_code,400)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'attending':'yes'}).status_code,302)
        self.client.force_login(User.objects.create_user('no-student'))
        self.assertEqual(self.client.post(self.url, {'attending':'yes'}).status_code,403)
        self.client.force_login(self.user)
        self.session.is_published=False
        self.session.save()
        self.assertEqual(self.client.post(self.url, {'attending':'yes'}).status_code,404)
        self.session.is_published=True
        self.session.end_time=timezone.now()-timedelta(seconds=1)
        self.session.save()
        self.assertEqual(self.client.post(self.url, {'attending':'yes'}).status_code,404)

    def test_staff_counts_and_four_languages(self):
        self.session.planned_students.add(self.student)
        self.user.is_staff=True
        self.user.save()
        for language in ('ja','en','fr','es'):
            response=self.client.get(reverse('home'), HTTP_ACCEPT_LANGUAGE=language)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.context['next_session']['obj'].planned_count,1)
        response=self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['sessions_display'][0]['obj'].planned_count,1)
