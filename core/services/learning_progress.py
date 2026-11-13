"""Read-only learning progress; never awards or deducts points."""
from datetime import datetime, time, timedelta
from django.utils import timezone
from core.models import GoldMembership, PointBalance, PointTransaction, UpcomingSession
from core.services.lesson_lifecycle import completed_lessons


def learning_progress(user, language_code=None):
    now = timezone.now()
    today = timezone.localdate(now)
    week = timezone.make_aware(datetime.combine(today-timedelta(days=today.weekday()), time.min))
    lessons = completed_lessons().filter(request__student__user=user, request__purpose='lesson').distinct()
    durations = lessons.values_list('started_at', 'end_at')
    seconds = sum(min(300, max(0, (end-start).total_seconds())) for start, end in durations)
    total = lessons.count()
    sessions = UpcomingSession.objects.filter(is_published=True, end_time__gt=now)
    field = {'ja':'japanese_count','en':'english_count','fr':'french_count','es':'spanish_count'}.get(language_code)
    if field:
        sessions = sessions.filter(**{field+'__gt':0})
    bonus = PointTransaction.objects.filter(user=user, transaction_type='signup_bonus', amount=2).exists()
    paid = PointTransaction.objects.filter(user=user, transaction_type='purchase', amount__gt=0).exists()
    gold = GoldMembership.objects.filter(user=user, expires_at__gt=now).exists()
    balance = PointBalance.objects.filter(user=user).values_list('student_balance', flat=True).first() or 0
    return {'total':total, 'weekly':lessons.filter(started_at__gte=week).count(),
            'minutes':int(seconds//60), 'trial_finished':bonus and total>=2 and balance<=0 and not paid and not gold,
            'next_session':sessions.order_by('start_time').first()}
