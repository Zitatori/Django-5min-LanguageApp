from datetime import timedelta
from unittest.mock import patch
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from core.models import (StudentProfile, TutorProfile, LessonLanguage, QuickLessonRequest,
                         QuickLessonMatch, PointBalance, PointTransaction, GoldMembership, ConversationNote, UpcomingSession)
from core.services.lesson_lifecycle import completed_lessons, settle_points
from core.views.student import active_tutors_qs
from core.consumers import VideoCallConsumer


class CallFixture:
    def setUp(self):
        self.now = timezone.now()
        self.student = StudentProfile.objects.create(user=User.objects.create_user('call-student'))
        self.tutor = TutorProfile.objects.create(user=User.objects.create_user('call-tutor'), is_online=True, online_since=self.now, last_ping_at=self.now)
        self.language = LessonLanguage.objects.create(code='ja', name='Japanese')
        self.tutor.languages.add(self.language)
        self.request = QuickLessonRequest.objects.create(student=self.student, language=self.language, status='matched')
        self.match = QuickLessonMatch.objects.create(request=self.request, tutor=self.tutor, student_joined_at=self.now, tutor_joined_at=self.now)
        self.balance = PointBalance.objects.create(user=self.student.user, student_balance=2)

    def connected(self, seconds=70):
        self.match.started_at = self.now-timedelta(seconds=seconds)
        self.match.end_at = self.now+timedelta(minutes=3)
        self.match.student_media_at = self.now
        self.match.tutor_media_at = self.now
        self.match.save()


class CallLifecycleTests(CallFixture, TestCase):
    def test_failed_exit_never_starts_or_charges_or_enters_history(self):
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.post(reverse('lesson_end', args=[self.match.pk])).status_code,200)
        self.match.refresh_from_db()
        self.assertIsNone(self.match.started_at)
        self.assertFalse(settle_points(self.match.pk))
        self.assertFalse(PointTransaction.objects.exists())
        self.assertFalse(completed_lessons().exists())
        self.assertEqual(self.client.get(reverse('lesson_rating', args=[self.match.pk])).status_code,302)
        from core.services.study_notes import collect_history
        ConversationNote.objects.create(student=self.student,tutor=self.tutor,match=self.match,talked_about='Weather')
        self.assertEqual(collect_history(self.student.user,'ja',False)[0],[])

    def test_unauthorized_user_cannot_join_end_or_rate(self):
        self.client.force_login(User.objects.create_user('outsider'))
        for name in ('lesson_room','lesson_end'):
            response = self.client.post(reverse(name,args=[self.match.pk]))
            self.assertEqual(response.status_code,403)
        self.match.refresh_from_db()
        self.assertIsNone(self.match.end_at)

    def test_points_require_elapsed_media_and_settle_once(self):
        self.connected(59)
        self.assertFalse(settle_points(self.match.pk,self.now))
        self.connected(70)
        self.assertTrue(settle_points(self.match.pk,self.now))
        self.assertFalse(settle_points(self.match.pk,self.now))
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.student_balance,1)
        self.assertEqual(PointBalance.objects.get(user=self.tutor.user).teacher_balance,1)
        self.assertEqual(PointTransaction.objects.count(),2)

    def test_future_scheduled_end_and_stale_media_are_not_enough(self):
        self.connected(70)
        self.match.tutor_media_at = self.now-timedelta(seconds=30)
        self.match.save()
        self.assertFalse(settle_points(self.match.pk,self.now))
        self.assertFalse(PointTransaction.objects.exists())

    def test_gold_and_hourly_pay_rules_are_preserved(self):
        self.connected()
        GoldMembership.objects.create(user=self.student.user,expires_at=self.now+timedelta(days=1))
        self.tutor.is_hourly_paid = True
        self.tutor.save()
        self.assertTrue(settle_points(self.match.pk,self.now))
        self.assertFalse(PointTransaction.objects.exists())
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.student_balance,2)

    def test_existing_transactions_prevent_duplicate_payments(self):
        self.connected()
        for user,kind,amount in [(self.student.user,'lesson_taken',-1),(self.tutor.user,'lesson_taught',1)]:
            PointTransaction.objects.create(user=user,transaction_type=kind,reference_id=self.match.pk,amount=amount)
        settle_points(self.match.pk,self.now)
        self.assertEqual(PointTransaction.objects.count(),2)

    def test_expired_reservation_no_longer_blocks_tutor(self):
        QuickLessonRequest.objects.filter(pk=self.request.pk).update(created_at=self.now-timedelta(minutes=3))
        self.assertIn(self.tutor,active_tutors_qs(self.language))
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.get(reverse('lesson_room',args=[self.match.pk])).status_code,302)

    def test_offline_intent_survives_heartbeat_and_online_does_not_end_call(self):
        self.client.force_login(self.tutor.user)
        self.client.post(reverse('tutor_set_offline'))
        self.match.end_at=self.now;self.match.save()
        self.client.get(reverse('tutor_match_status'))
        self.tutor.refresh_from_db()
        self.assertFalse(self.tutor.is_online)
        self.connected()
        self.client.post(reverse('tutor_dashboard'),{'action':'go_online'})
        self.match.refresh_from_db()
        self.assertEqual(self.match.started_at,self.now-timedelta(seconds=70))
        self.assertGreater(self.match.end_at,self.now)

    def test_completed_filters_do_not_count_zero_duration_or_not_held(self):
        self.connected(300)
        self.match.end_at=self.now;self.match.save()
        self.assertEqual(completed_lessons().count(),1)
        ConversationNote.objects.create(student=self.student,tutor=self.tutor,match=self.match,conversation_not_held=True)
        self.assertFalse(completed_lessons().exists())

    def test_published_schedule_is_language_specific(self):
        UpcomingSession.objects.create(start_time=self.now+timedelta(hours=1),end_time=self.now+timedelta(hours=2),is_published=True,french_count=1)
        session=UpcomingSession.objects.create(start_time=self.now+timedelta(hours=3),end_time=self.now+timedelta(hours=4),is_published=True,japanese_count=1)
        self.client.force_login(self.student.user)
        data=self.client.get(reverse('student_online_counts')).json()[str(self.language.pk)]
        self.assertEqual(data['next_session']['start'],session.start_time.isoformat())


class CallSocketTests(CallFixture, TransactionTestCase):
    def communicator(self,user):
        communicator=WebsocketCommunicator(VideoCallConsumer.as_asgi(),'/ws/lesson/%s/'%self.match.pk)
        communicator.scope['user']=user
        communicator.scope['url_route']={'kwargs':{'match_id':self.match.pk}}
        return communicator

    def test_socket_denies_anonymous_and_non_participant(self):
        outsider=User.objects.create_user('socket-outsider')
        async def run():
            for user in [AnonymousUser(),outsider]:
                c=self.communicator(user)
                connected,_=await c.connect()
                self.assertFalse(connected)
                await c.disconnect()
        async_to_sync(run)()

    def test_both_participants_must_confirm_and_sender_cannot_be_forged(self):
        async def run():
            a,b=self.communicator(self.student.user),self.communicator(self.tutor.user)
            self.assertTrue((await a.connect())[0]);self.assertTrue((await b.connect())[0])
            await a.send_json_to({'type':'join','sender':999})
            data=await b.receive_json_from()
            self.assertEqual(data['sender'],self.student.user.pk)
            await a.send_json_to({'type':'webrtc_connected'})
            self.assertTrue(await b.receive_nothing(timeout=.05))
            await b.send_json_to({'type':'webrtc_connected'})
            timer=await a.receive_json_from()
            self.assertEqual(timer['type'],'timer_start')
            self.assertGreaterEqual(timer['seconds'],299)
            await a.disconnect();await b.disconnect()
        async_to_sync(run)()
        self.match.refresh_from_db()
        self.assertIsNotNone(self.match.started_at)
        self.assertFalse(PointTransaction.objects.exists())
