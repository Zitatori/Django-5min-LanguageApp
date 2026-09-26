from datetime import timedelta
from unittest.mock import patch

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
from core.views.student import _claim_tutor_for_match, active_tutors_qs, _in_lesson_info


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

    def test_wait_time_includes_one_minute_for_notes(self):
        now = timezone.now()
        QuickLessonMatch.objects.create(
            request=self._request(), tutor=self.tutor,
            started_at=now, end_at=now + timedelta(minutes=5),
        )
        self.assertEqual(_in_lesson_info(self.language, now), (1, 6))
        self.assertEqual(_in_lesson_info(self.language, now + timedelta(minutes=5)), (1, 1))
        self.assertEqual(_in_lesson_info(self.language, now + timedelta(minutes=5, seconds=59)), (1, 1))
        self.assertEqual(_in_lesson_info(self.language, now + timedelta(minutes=6)), (0, None))

    def test_note_period_prevents_matching_until_exactly_one_minute_after_end(self):
        now = timezone.now()
        QuickLessonMatch.objects.create(
            request=self._request(), tutor=self.tutor,
            started_at=now - timedelta(minutes=5), end_at=now,
        )
        with patch("core.views.student.timezone.now", return_value=now + timedelta(seconds=59)):
            self.assertNotIn(self.tutor, active_tutors_qs(language=self.language))
            self.assertFalse(_claim_tutor_for_match(self.tutor))
        with patch("core.views.student.timezone.now", return_value=now + timedelta(seconds=60)):
            self.assertIn(self.tutor, active_tutors_qs(language=self.language))
            self.assertTrue(_claim_tutor_for_match(self.tutor))

    def test_note_period_is_shown_even_when_tutor_is_offline(self):
        now = timezone.now()
        self.tutor.is_online = False
        self.tutor.save()
        QuickLessonMatch.objects.create(
            request=self._request(), tutor=self.tutor,
            started_at=now - timedelta(minutes=2), end_at=now - timedelta(seconds=10),
        )
        self.client.force_login(self.student.user)
        from django.urls import reverse
        response = self.client.get(reverse("student_online_counts"))
        info = response.json()[str(self.language.pk)]
        self.assertEqual(info["online"], 0)
        self.assertEqual(info["in_lesson"], 1)
        self.assertEqual(info["soonest_minutes"], 1)
