"""Shared call eligibility, reservation leases and atomic point settlement."""
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from core.models import QuickLessonMatch, PointBalance, PointTransaction, GoldMembership

CONNECT_LEASE_SECONDS = 120
PRESENCE_SECONDS = 90
NOTE_SECONDS = 60


def active_calls(now=None, include_notes=False):
    now = now or timezone.now()
    return (Q(started_at__isnull=True, end_at__isnull=True,
              request__status='matched', request__created_at__gt=now-timedelta(seconds=CONNECT_LEASE_SECONDS))
            | Q(started_at__isnull=False, end_at__gt=now-timedelta(seconds=NOTE_SECONDS if include_notes else 0)))


def completed_lessons():
    # Legacy rows have no media timestamps: retain positive-duration history, never
    # rewrite old balances. Zero-duration fallbacks are not completed conversations.
    return QuickLessonMatch.objects.filter(
        started_at__isnull=False, end_at__lte=timezone.now(),
        end_at__gte=F('started_at')+timedelta(seconds=1),
        student_joined_at__isnull=False, tutor_joined_at__isnull=False,
    ).exclude(conversationnote__conversation_not_held=True)


@transaction.atomic
def settle_points(match_id, now=None):
    now = now or timezone.now()
    match = QuickLessonMatch.objects.select_for_update().select_related(
        'request__student__user', 'tutor__user').get(pk=match_id)
    if match.points_settled_at or not match.started_at or not match.end_at:
        return False
    # Both clients must have recently reported actual media connectivity. A planned
    # five-minute end_at alone is never evidence of a minute of conversation.
    if not match.student_media_at or not match.tutor_media_at:
        return False
    through = min(now, match.end_at, match.student_media_at, match.tutor_media_at)
    if (through-match.started_at).total_seconds() < 60:
        return False
    if (now-min(match.student_media_at, match.tutor_media_at)).total_seconds() > 20:
        return False
    if match.conversationnote_set.filter(conversation_not_held=True).exists():
        return False
    # Match lock serializes all workers; balance locks also protect simultaneous
    # lessons sharing a user. Existing transactions remain authoritative.
    users = sorted({match.request.student.user_id, match.tutor.user_id})
    for user_id in users:
        PointBalance.objects.get_or_create(user_id=user_id)
    balances = {b.user_id:b for b in PointBalance.objects.select_for_update().filter(user_id__in=users).order_by('user_id')}
    student_id, tutor_id = match.request.student.user_id, match.tutor.user_id
    for user_id, kind, amount, field, skip in (
        (student_id, PointTransaction.TYPE_LESSON_TAKEN, -1, 'student_balance', GoldMembership.objects.filter(user_id=student_id, expires_at__gt=now).exists()),
        (tutor_id, PointTransaction.TYPE_LESSON_TAUGHT, 1, 'teacher_balance', match.tutor.is_hourly_paid),
    ):
        if skip or PointTransaction.objects.filter(user_id=user_id, transaction_type=kind, reference_id=match.pk).exists():
            continue
        balance = balances[user_id]
        if amount < 0 and balance.student_balance < 1:
            continue
        setattr(balance, field, getattr(balance, field)+amount)
        balance.save(update_fields=[field])
        PointTransaction.objects.create(user_id=user_id, amount=amount, transaction_type=kind, reference_id=match.pk)
    match.points_settled_at = now
    match.save(update_fields=['points_settled_at'])
    return True
