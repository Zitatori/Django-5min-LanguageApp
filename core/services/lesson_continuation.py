"""Continue after a lesson: extend with the same tutor or move to another one.

An extension adds five minutes to the running match. The student asks, the
tutor accepts, and one point moves on acceptance (Gold students and hourly-paid
tutors are skipped, as in the normal settlement). Moving to another tutor
reserves the new tutor first, so the current call only ends once a next
lesson actually exists.
"""
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from core.models import (GoldMembership, PointBalance, PointTransaction, QuickLessonMatch,
                         QuickLessonRequest, TutorProfile)
from core.services.lesson_lifecycle import settle_points

EXTENSION_MINUTES = 5


def broadcast(match_id, message):
    """Send a message to everyone in the lesson's WebSocket room."""
    async_to_sync(get_channel_layer().group_send)(
        f'lesson_{match_id}', {'type': 'send_signal', 'message': message, 'sender_channel_name': ''})


def _is_gold(user_id, now):
    return GoldMembership.objects.filter(user_id=user_id, expires_at__gt=now).exists()


def points_needed(match, now):
    """Points the student still needs for one more five-minute block."""
    if _is_gold(match.request.student.user_id, now):
        return 0
    return 1 if match.points_settled_at else 2


def can_pay(match, now=None):
    now = now or timezone.now()
    needed = points_needed(match, now)
    if needed == 0:
        return True
    balance = PointBalance.objects.filter(user_id=match.request.student.user_id).first()
    return bool(balance and balance.student_balance >= needed)


def other_tutors(match):
    from core.views.student import active_tutors_qs
    return active_tutors_qs(language=match.request.language).exclude(pk=match.tutor_id)


def _running(match, now):
    return bool(match.started_at and match.end_at and match.end_at > now)


@transaction.atomic
def request_extension(match_id, now=None):
    now = now or timezone.now()
    match = QuickLessonMatch.objects.select_for_update().select_related('request__student').get(pk=match_id)
    if not _running(match, now) or not can_pay(match, now):
        return False
    match.extension_requested_at = now
    match.save(update_fields=['extension_requested_at'])
    return True


@transaction.atomic
def decline_extension(match_id):
    return QuickLessonMatch.objects.filter(pk=match_id, extension_requested_at__isnull=False).update(
        extension_requested_at=None) == 1


@transaction.atomic
def accept_extension(match_id, now=None):
    """Charge one block and add five minutes. Returns the new end time or None."""
    now = now or timezone.now()
    match = QuickLessonMatch.objects.select_for_update().select_related(
        'request__student', 'tutor').get(pk=match_id)
    if not match.extension_requested_at or not _running(match, now) or not can_pay(match, now):
        return None
    number = match.extension_count + 1
    student_id, tutor_id = match.request.student.user_id, match.tutor.user_id
    users = sorted({student_id, tutor_id})
    for user_id in users:
        PointBalance.objects.get_or_create(user_id=user_id)
    balances = {b.user_id: b for b in PointBalance.objects.select_for_update().filter(user_id__in=users).order_by('user_id')}
    for user_id, kind, amount, field, skip in (
        (student_id, PointTransaction.TYPE_LESSON_TAKEN, -1, 'student_balance', _is_gold(student_id, now)),
        (tutor_id, PointTransaction.TYPE_LESSON_TAUGHT, 1, 'teacher_balance', match.tutor.is_hourly_paid),
    ):
        if skip:
            continue
        balance = balances[user_id]
        setattr(balance, field, getattr(balance, field) + amount)
        balance.save(update_fields=[field])
        PointTransaction.objects.create(user_id=user_id, amount=amount, transaction_type=kind,
                                        reference_id=match.pk, note=f'extension {number}')
    match.end_at += timedelta(minutes=EXTENSION_MINUTES)
    match.extension_count = number
    match.extension_requested_at = None
    match.save(update_fields=['end_at', 'extension_count', 'extension_requested_at'])
    return match.end_at


def move_to_next_tutor(match_id, now=None):
    """Reserve another tutor in the same language, then end the current call.

    Returns the new request, or None when nobody is free or points are short.
    The current lesson keeps running when this returns None.
    """
    now = now or timezone.now()
    with transaction.atomic():
        match = QuickLessonMatch.objects.select_for_update().select_related(
            'request__student', 'request__language').get(pk=match_id)
        if not _running(match, now) or not can_pay(match, now):
            return None
        from core.views.student import _claim_tutor_for_match
        new_request = None
        for tutor in other_tutors(match).order_by('?')[:5]:
            if _claim_tutor_for_match(tutor):
                new_request = QuickLessonRequest.objects.create(
                    student=match.request.student, language=match.request.language,
                    purpose='lesson', status='matched')
                QuickLessonMatch.objects.create(request=new_request, tutor=tutor, price=5.0)
                break
        if new_request is None:
            return None
        match.end_at = now
        match.extension_requested_at = None
        match.save(update_fields=['end_at', 'extension_requested_at'])
    settle_points(match_id, now)
    TutorProfile.objects.filter(pk=match.tutor_id).update(is_online=False)
    return new_request
