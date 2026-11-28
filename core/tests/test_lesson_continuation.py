from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from core.models import (TutorProfile, PointBalance, PointTransaction, GoldMembership,
                         QuickLessonMatch, QuickLessonRequest)
from core.services.lesson_lifecycle import settle_points
from core.tests.test_call_lifecycle import CallFixture


class ContinuationFixture(CallFixture):
    def setUp(self):
        super().setUp()
        self.connected(270)  # 4:30 into the lesson, already settled
        self.match.end_at = timezone.now()+timedelta(seconds=30)
        self.match.save()
        settle_points(self.match.pk)
        self.balance.refresh_from_db()

    def other_tutor(self, name='other-tutor'):
        now = timezone.now()
        tutor = TutorProfile.objects.create(user=User.objects.create_user(name), is_online=True, online_since=now, last_ping_at=now)
        tutor.languages.add(self.language)
        return tutor


class ExtensionTests(ContinuationFixture, TestCase):
    def extend(self, user, action):
        self.client.force_login(user)
        return self.client.post(reverse('lesson_extend', args=[self.match.pk]), {'action': action})

    def test_student_asks_tutor_accepts_and_one_point_moves(self):
        before_end = QuickLessonMatch.objects.get(pk=self.match.pk).end_at
        self.assertEqual(self.extend(self.student.user, 'request').status_code, 200)
        self.assertEqual(self.extend(self.tutor.user, 'accept').status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.end_at-before_end, timedelta(minutes=5))
        self.assertEqual(self.match.extension_count, 1)
        self.assertIsNone(self.match.extension_requested_at)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.student_balance, 0)
        self.assertEqual(PointBalance.objects.get(user=self.tutor.user).teacher_balance, 2)
        self.assertEqual(PointTransaction.objects.filter(note='extension 1').count(), 2)
        # A second accept without a new request does nothing.
        self.assertEqual(self.extend(self.tutor.user, 'accept').status_code, 409)

    def test_tutor_cannot_accept_without_request_and_student_cannot_accept(self):
        self.assertEqual(self.extend(self.tutor.user, 'accept').status_code, 409)
        self.extend(self.student.user, 'request')
        self.assertEqual(self.extend(self.student.user, 'accept').status_code, 400)

    def test_decline_keeps_end_and_points(self):
        self.extend(self.student.user, 'request')
        self.assertEqual(self.extend(self.tutor.user, 'decline').status_code, 200)
        self.match.refresh_from_db()
        self.assertIsNone(self.match.extension_requested_at)
        self.assertEqual(self.match.extension_count, 0)
        self.assertEqual(PointTransaction.objects.filter(note__startswith='extension').count(), 0)

    def test_no_points_means_no_extension_but_gold_is_free(self):
        self.balance.student_balance = 0
        self.balance.save()
        self.assertEqual(self.extend(self.student.user, 'request').status_code, 409)
        GoldMembership.objects.create(user=self.student.user, expires_at=timezone.now()+timedelta(days=1))
        self.assertEqual(self.extend(self.student.user, 'request').status_code, 200)
        self.assertEqual(self.extend(self.tutor.user, 'accept').status_code, 200)
        self.assertFalse(PointTransaction.objects.filter(user=self.student.user, note='extension 1').exists())

    def test_finished_lesson_cannot_be_extended(self):
        self.match.end_at = timezone.now()-timedelta(seconds=1)
        self.match.save()
        self.assertEqual(self.extend(self.student.user, 'request').status_code, 409)

    def test_extension_never_blocks_the_base_settlement(self):
        PointTransaction.objects.all().delete()
        QuickLessonMatch.objects.filter(pk=self.match.pk).update(points_settled_at=None)
        self.balance.student_balance = 3
        self.balance.save()
        self.extend(self.student.user, 'request')
        self.extend(self.tutor.user, 'accept')
        self.match.refresh_from_db()
        self.match.student_media_at = self.match.tutor_media_at = timezone.now()
        self.match.save()
        self.assertTrue(settle_points(self.match.pk))
        self.assertEqual(PointTransaction.objects.filter(user=self.student.user).count(), 2)

    def test_outsider_is_forbidden(self):
        self.assertEqual(self.extend(User.objects.create_user('outsider'), 'request').status_code, 403)


class NextTutorTests(ContinuationFixture, TestCase):
    def test_options_count_only_other_free_tutors(self):
        self.client.force_login(self.student.user)
        url = reverse('lesson_continue_options', args=[self.match.pk])
        self.assertEqual(self.client.get(url).json()['other_tutors'], 0)
        self.other_tutor()
        data = self.client.get(url).json()
        self.assertEqual(data['other_tutors'], 1)
        self.assertTrue(data['can_pay'])
        self.client.force_login(self.tutor.user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_moves_to_another_tutor_and_ends_this_call(self):
        other = self.other_tutor()
        self.client.force_login(self.student.user)
        response = self.client.post(reverse('lesson_next_tutor', args=[self.match.pk]))
        self.assertEqual(response.status_code, 200)
        new_request = QuickLessonRequest.objects.exclude(pk=self.request.pk).get()
        self.assertEqual(response.json()['url'], reverse('request_detail', args=[new_request.pk]))
        self.assertEqual(new_request.quicklessonmatch.tutor, other)
        self.assertEqual(new_request.language, self.language)
        self.match.refresh_from_db()
        self.assertLessEqual(self.match.end_at, timezone.now())

    def test_nobody_free_keeps_the_lesson_running(self):
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.post(reverse('lesson_next_tutor', args=[self.match.pk])).status_code, 409)
        self.match.refresh_from_db()
        self.assertGreater(self.match.end_at, timezone.now())
        self.assertEqual(QuickLessonRequest.objects.count(), 1)

    def test_next_tutor_is_called_into_the_new_room_with_the_student(self):
        other = self.other_tutor()
        self.client.force_login(self.student.user)
        detail = self.client.post(reverse('lesson_next_tutor', args=[self.match.pk])).json()['url']
        new_match = QuickLessonMatch.objects.get(tutor=other)
        room = reverse('lesson_room', args=[new_match.pk])
        self.assertContains(self.client.get(detail), room)
        self.assertEqual(self.client.get(room).status_code, 200)
        self.client.force_login(other.user)
        self.assertEqual(self.client.get(reverse('tutor_match_status')).json(), {'matched': True, 'room_url': room})
        self.assertEqual(self.client.get(room).status_code, 200)
        # The tutor the student left is not called back into the old room.
        self.client.force_login(self.tutor.user)
        self.assertFalse(self.client.get(reverse('tutor_match_status')).json()['matched'])

    def test_a_press_in_the_last_second_still_moves_within_the_grace(self):
        self.other_tutor()
        ended = timezone.now()-timedelta(seconds=3)
        QuickLessonMatch.objects.filter(pk=self.match.pk).update(end_at=ended)
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.post(reverse('lesson_next_tutor', args=[self.match.pk])).status_code, 200)
        self.match.refresh_from_db()
        self.assertEqual(self.match.end_at, ended)

    def test_a_lesson_long_over_cannot_move(self):
        self.other_tutor()
        QuickLessonMatch.objects.filter(pk=self.match.pk).update(end_at=timezone.now()-timedelta(seconds=30))
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.post(reverse('lesson_next_tutor', args=[self.match.pk])).status_code, 409)

    def test_room_shows_continue_buttons_to_student_and_answer_buttons_to_tutor(self):
        self.client.force_login(self.student.user)
        page = self.client.get(reverse('lesson_room', args=[self.match.pk]))
        self.assertContains(page, 'id="extend-btn"')
        self.assertNotContains(page, 'id="extend-accept"')
        self.client.force_login(self.tutor.user)
        page = self.client.get(reverse('lesson_room', args=[self.match.pk]))
        self.assertContains(page, 'id="extend-accept"')
        self.assertNotContains(page, 'id="extend-btn"')
