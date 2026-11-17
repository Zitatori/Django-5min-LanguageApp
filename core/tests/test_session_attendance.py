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

    def test_admin_attendee_identity_and_cancellation(self):
        self.user.first_name='Attendance Nickname'
        self.user.email='attendance-only@example.com'
        self.user.save()
        self.session.planned_students.add(self.student)
        admin=User.objects.create_user('staff-viewer',is_staff=True)
        self.client.force_login(admin)
        response=self.client.get(reverse('admin_dashboard'))
        self.assertContains(response,'Attendance Nickname')
        self.assertContains(response,'id="session-attendees-{}"'.format(self.session.pk))
        section=response.content.decode().split('id="session-attendees-{}"'.format(self.session.pk))[1].split('</details>')[0]
        self.assertIn('attendance-only@example.com',section)
        self.session.planned_students.remove(self.student)
        response=self.client.get(reverse('admin_dashboard'))
        section=response.content.decode().split('id="session-attendees-{}"'.format(self.session.pk))[1].split('</details>')[0]
        self.assertNotIn('Attendance Nickname',section)
        self.assertNotIn('attendance-only@example.com',section)

    def test_attendee_list_is_admin_only(self):
        from core.models import UserProfile, TutorProfile
        self.session.planned_students.add(self.student)
        self.user.email='hidden-attendee@example.com';self.user.save()
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code,403)
        outsider=User.objects.create_user('outsider')
        TutorProfile.objects.create(user=outsider)
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code,403)
        self.assertNotContains(self.client.get(reverse('home')),'hidden-attendee@example.com')
        UserProfile.objects.update_or_create(user=outsider,defaults={'role':'Admin'})
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code,200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code,302)
