from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import LessonLanguage, QuickLessonMatch, QuickLessonRequest, StudentProfile, TutorProfile


class TutorFeedbackTests(TestCase):
    def setUp(self):
        self.tutor = TutorProfile.objects.create(user=User.objects.create_user(username='feedback-tutor'))
        student = StudentProfile.objects.create(user=User.objects.create_user(username='feedback-student'))
        language = LessonLanguage.objects.create(code='en', name='English')
        lesson_request = QuickLessonRequest.objects.create(student=student, language=language, status='matched')
        self.match = QuickLessonMatch.objects.create(
            request=lesson_request, tutor=self.tutor, student_joined_at=timezone.now(),
            started_at=timezone.now(), end_at=timezone.now(), student_rating=4,
            student_feedback='Helpful lesson! <script>alert(1)</script>',
        )
        self.client.force_login(self.tutor.user)

    def test_own_feedback_is_visible_and_escaped(self):
        response = self.client.get(reverse('tutor_dashboard'))
        self.assertContains(response, '4 / 5')
        self.assertContains(response, 'Helpful lesson! &lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_other_tutor_cannot_see_feedback(self):
        other = User.objects.create_user(username='other-tutor')
        TutorProfile.objects.create(user=other)
        self.client.force_login(other)
        response = self.client.get(reverse('tutor_dashboard'))
        self.assertNotContains(response, 'Helpful lesson!')
        self.assertNotContains(response, '4 / 5')

    def test_unrated_lesson_does_not_show_zero_rating(self):
        self.match.student_rating = None
        self.match.student_feedback = ''
        self.match.save()
        response = self.client.get(reverse('tutor_dashboard'))
        self.assertNotContains(response, '0 / 5')
        self.assertNotContains(response, '★')
