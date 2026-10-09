from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from core.models import LessonLanguage, QuickLessonMatch, QuickLessonRequest, StudentProfile, TutorProfile


class PrivateNoteTests(TestCase):
    def setUp(self):
        self.student = StudentProfile.objects.create(user=User.objects.create_user(username='private-student'))
        self.tutor = TutorProfile.objects.create(user=User.objects.create_user(username='private-tutor'))
        language = LessonLanguage.objects.create(code='en', name='English')
        req = QuickLessonRequest.objects.create(student=self.student, language=language)
        self.match = QuickLessonMatch.objects.create(request=req, tutor=self.tutor, student_joined_at=timezone.now(), tutor_joined_at=timezone.now(), started_at=timezone.now(), end_at=timezone.now())
        self.url = reverse('lesson_rating', args=[self.match.pk])
        self.client.force_login(self.student.user)

    def test_note_without_rating_and_student_history(self):
        self.client.post(self.url, {'private_note': 'My private practice plan'})
        self.match.refresh_from_db()
        self.assertEqual(self.match.student_private_note, 'My private practice plan')
        self.assertIsNone(self.match.student_rating)
        self.assertContains(self.client.get(reverse('create_request')), 'My private practice plan')
        self.client.force_login(self.tutor.user)
        self.assertNotContains(self.client.get(reverse('tutor_dashboard')), 'My private practice plan')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'private_note': 'Changed'}).status_code, 404)

    def test_note_can_be_updated_after_rating_without_changing_feedback(self):
        self.client.post(self.url, {'rating': '5', 'feedback': 'Thank you', 'private_note': 'Original'})
        self.assertContains(self.client.get(self.url), 'name="private_note"')
        self.client.post(self.url, {'private_note': 'Updated'})
        self.match.refresh_from_db()
        self.assertEqual(self.match.student_rating, 5)
        self.assertEqual(self.match.student_feedback, 'Thank you')
        self.assertEqual(self.match.student_private_note, 'Updated')
