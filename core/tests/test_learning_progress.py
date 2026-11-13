from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from core.models import (StudentProfile,TutorProfile,LessonLanguage,QuickLessonRequest,QuickLessonMatch,
    PointBalance,PointTransaction,GoldMembership,UpcomingSession,LearningEvent,ConversationNote)
from core.services.learning_progress import learning_progress


class ProgressTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('progress',password='secret')
        self.student=StudentProfile.objects.create(user=self.user)
        self.tutor=TutorProfile.objects.create(user=User.objects.create_user('teacher'))
        self.language=LessonLanguage.objects.create(code='fr',name='French')
        self.balance=PointBalance.objects.create(user=self.user,student_balance=0)
        PointTransaction.objects.create(user=self.user,transaction_type='signup_bonus',amount=2)
        self.client.force_login(self.user)

    def lesson(self,connected=True):
        now=timezone.now()
        req=QuickLessonRequest.objects.create(student=self.student,language=self.language,status='matched')
        return QuickLessonMatch.objects.create(request=req,tutor=self.tutor,started_at=now-timedelta(minutes=6),end_at=now-timedelta(minutes=1),student_joined_at=now-timedelta(minutes=6) if connected else None,tutor_joined_at=now-timedelta(minutes=6) if connected else None)

    def test_real_lessons_only_and_balances_unchanged(self):
        self.lesson();self.lesson();failed=self.lesson(False)
        result=learning_progress(self.user)
        self.assertEqual(result['total'],2);self.assertEqual(result['minutes'],10)
        self.assertTrue(result['trial_finished'])
        self.assertEqual(self.client.get(reverse('lesson_rating',args=[failed.pk])).status_code,302)
        self.balance.refresh_from_db();self.assertEqual(self.balance.student_balance,0)
        self.assertEqual(PointTransaction.objects.count(),1)

    def test_no_trial_banner_for_gold_purchased_or_remaining_credit(self):
        self.lesson();self.lesson()
        self.balance.student_balance=1;self.balance.save()
        self.assertFalse(learning_progress(self.user)['trial_finished'])
        self.balance.student_balance=0;self.balance.save()
        gm=GoldMembership.objects.create(user=self.user,expires_at=timezone.now()+timedelta(days=1))
        self.assertFalse(learning_progress(self.user)['trial_finished']);gm.delete()
        PointTransaction.objects.create(user=self.user,transaction_type='purchase',amount=10)
        self.assertFalse(learning_progress(self.user)['trial_finished'])

    def test_language_schedule_and_render_four_languages(self):
        match=self.lesson()
        now=timezone.now()
        UpcomingSession.objects.create(start_time=now+timedelta(hours=1),end_time=now+timedelta(hours=2),japanese_count=1,is_published=True)
        fr=UpcomingSession.objects.create(start_time=now+timedelta(hours=3),end_time=now+timedelta(hours=4),french_count=1,is_published=True)
        self.assertEqual(learning_progress(self.user,'fr')['next_session'],fr)
        for lang in ('ja','en','fr','es'):
            res=self.client.get(reverse('lesson_rating',args=[match.pk]),HTTP_ACCEPT_LANGUAGE=lang)
            self.assertContains(res,'celebration-bird');self.assertContains(res,'prefers-reduced-motion')
            self.assertContains(res,'name="rating"')
            self.assertEqual(self.client.get(reverse('home'),HTTP_ACCEPT_LANGUAGE=lang).status_code,200)
        other=User.objects.create_user('other');self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('lesson_rating',args=[match.pk])).status_code,404)

    def test_event_deduplication_and_admin_permissions(self):
        self.lesson();self.lesson()
        for _ in range(2):self.assertEqual(self.client.get(reverse('purchase_points')).status_code,200)
        self.assertEqual(LearningEvent.objects.count(),1)
        url=reverse('learning_retention')
        self.assertEqual(self.client.get(url).status_code,403)
        self.user.is_staff=True;self.user.save()
        res=self.client.get(url);self.assertEqual(res.status_code,200)
        self.assertEqual(res.context['rows'][0][1],1)
        self.assertEqual(res.context['rows'][1][1],1)

    def test_not_held_excluded(self):
        match=self.lesson()
        ConversationNote.objects.create(student=self.student,tutor=self.tutor,match=match,conversation_not_held=True)
        self.assertEqual(learning_progress(self.user)['total'],0)
