from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.models import (
    LessonLanguage,
    QuickLessonMatch,
    QuickLessonRequest,
    StudentProfile,
    TutorProfile,
)
from core.views.student import _claim_tutor_for_match, active_tutors_qs


class TutorAvailabilityTests(TestCase):
    def setUp(self):
        self.language = LessonLanguage.objects.create(code="en", name="English")
        self.tutor_user = User.objects.create_user(username="teacher")
        self.tutor = TutorProfile.objects.create(
            user=self.tutor_user,
            is_online=True,
            last_ping_at=timezone.now(),
        )
        self.tutor.languages.add(self.language)
        self.student = StudentProfile.objects.create(
            user=User.objects.create_user(username="student")
        )

    def _request(self):
        return QuickLessonRequest.objects.create(
            student=self.student,
            language=self.language,
            status="matched",
        )

    def test_active_match_excludes_tutor_even_if_online_flag_is_true(self):
        QuickLessonMatch.objects.create(
            request=self._request(),
            tutor=self.tutor,
        )

        self.assertNotIn(self.tutor, list(active_tutors_qs(language=self.language)))
        self.assertFalse(_claim_tutor_for_match(self.tutor))

    def test_ended_match_allows_tutor_to_be_available_again(self):
        now = timezone.now()
        QuickLessonMatch.objects.create(
            request=self._request(),
            tutor=self.tutor,
            started_at=now - timedelta(minutes=10),
            end_at=now - timedelta(minutes=5),
        )

        self.assertIn(self.tutor, list(active_tutors_qs(language=self.language)))
        self.assertTrue(_claim_tutor_for_match(self.tutor))
