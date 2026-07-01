import json
from collections import defaultdict
from zoneinfo import ZoneInfo
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField, Count, Q
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage, QuickLessonRequest
from core.models import PointBalance, PointTransaction, WithdrawalRequest
from core.models import GoldMembership, GoldSubscriptionRequest
from core.models import UpcomingSession
from datetime import timedelta, datetime

JST = ZoneInfo('Asia/Tokyo')

INITIAL_BONUS = 10

def staff_or_admin_role_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff or (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Admin'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You don't have permission to access this page.")
    return wrapper

@staff_or_admin_role_required
def admin_dashboard(request):
    users = (
        User.objects
        .select_related('userprofile', 'tutorprofile', 'point_balance', 'gold_membership')
        .prefetch_related('tutorprofile__languages')
        .annotate(
            is_online_sort=Case(
                When(tutorprofile__is_online=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            lesson_count=Count('tutorprofile__quicklessonmatch', distinct=True),
        )
        .order_by('-date_joined')
    )
    users_list    = list(users)
    recent_users  = users_list[:15]
    older_users   = users_list[15:]
    tutors = TutorProfile.objects.select_related('user').prefetch_related('languages').all()
    all_matches = QuickLessonMatch.objects.filter(
        student_joined_at__isnull=False,
        tutor_joined_at__isnull=False,
        started_at__isnull=False,
    ).select_related(
        'request__student__user',
        'request__language',
        'tutor__user',
    ).order_by('-started_at')

    now_dt = timezone.now()
    live_matches   = [m for m in all_matches if m.end_at and m.end_at > now_dt]
    past_matches   = [m for m in all_matches if not (m.end_at and m.end_at > now_dt)]
    recent_matches = past_matches[:15]
    older_matches  = past_matches[15:]
    matches = all_matches  # user_matches_dict 用に全件保持

    languages = LessonLanguage.objects.all()

    # ユーザーごとの会話履歴（Student/Tutor 両方の視点）
    user_matches_dict = defaultdict(list)
    for m in matches:
        lang_name = m.request.language.name
        date_str = m.started_at.strftime('%m/%d %H:%M')
        student_uid = m.request.student.user_id
        tutor_uid = m.tutor.user_id
        user_matches_dict[student_uid].append({
            'role': 'student',
            'partner': m.tutor.user.username,
            'language': lang_name,
            'date': date_str,
        })
        user_matches_dict[tutor_uid].append({
            'role': 'tutor',
            'partner': m.request.student.user.username,
            'language': lang_name,
            'date': date_str,
        })
    user_matches_json = json.dumps(dict(user_matches_dict))

    # 言語別オンライン講師（30分以内にpingがあるものだけ）
    ping_cutoff = timezone.now() - timedelta(seconds=1800)
    online_tutors = (
        TutorProfile.objects
        .filter(
            is_online=True,
        )
        .filter(
            Q(last_ping_at__isnull=True) | Q(last_ping_at__gte=ping_cutoff)
        )
        .select_related('user')
        .prefetch_related('languages')
        .order_by('user__username')
    )
    online_by_language = defaultdict(list)
    for tutor in online_tutors:
        for lang in tutor.languages.all():
            online_by_language[lang.name].append(tutor)
    online_by_language_list = [
        (lang_name, tutors_list)
        for lang_name, tutors_list in sorted(online_by_language.items())
    ]

    no_balance_count = User.objects.filter(point_balance__isnull=True).count()
    withdrawal_requests = WithdrawalRequest.objects.select_related('user').order_by('-created_at')
    gold_requests = GoldSubscriptionRequest.objects.select_related('user').filter(
        status=GoldSubscriptionRequest.STATUS_PENDING
    )
    all_sessions = UpcomingSession.objects.order_by('start_time')
    CET = ZoneInfo('Europe/Zurich')
    sessions_display = []
    for s in all_sessions:
        cet_start = s.start_time.astimezone(CET)
        cet_end   = s.end_time.astimezone(CET)
        sessions_display.append({
            'obj':       s,
            'cet_start': cet_start,
            'cet_end':   cet_end,
            # Pre-formatted strings to avoid Django template filter TZ conversion
            'date_str':  cet_start.strftime('%Y-%m-%d'),
            'start_str': cet_start.strftime('%H:%M'),
            'end_str':   cet_end.strftime('%H:%M'),
        })

    return render(request, 'core/admin_dashboard.html', {
        'users':               users,
        'users_count':         len(users_list),
        'recent_users':        recent_users,
        'older_users':         older_users,
        'tutors':              tutors,
        'live_matches':        live_matches,
        'recent_matches':      recent_matches,
        'older_matches':       older_matches,
        'languages':           languages,
        'user_matches_json':   user_matches_json,
        'no_balance_count':    no_balance_count,
        'withdrawal_requests': withdrawal_requests,
        'gold_requests':            gold_requests,
        'sessions_display':         sessions_display,
        'online_by_language_list':  online_by_language_list,
        'online_tutors_count':      online_tutors.count(),
    })

@staff_or_admin_role_required
def update_tutor_languages(request, tutor_id):
    if request.method == 'POST':
        tutor = get_object_or_404(TutorProfile, id=tutor_id)
        lang_ids = request.POST.getlist('languages')
        tutor.languages.set(lang_ids)
        return redirect('admin_dashboard')


@staff_or_admin_role_required
def update_user_languages(request, user_id):
    """StudentでもTutorProfileを作成して言語を設定する"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        tutor, _ = TutorProfile.objects.get_or_create(user=user)
        lang_ids = request.POST.getlist('languages')
        tutor.languages.set(lang_ids)
        return redirect('admin_dashboard')

@staff_or_admin_role_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:
            user.delete()
    return redirect('admin_dashboard')

@staff_or_admin_role_required
def update_user_points(request, user_id):
    """管理者がユーザーの生徒ポイントを加算・減算する"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        try:
            delta = int(request.POST.get('student_points_delta', 0))
        except ValueError:
            return redirect('admin_dashboard')

        if delta == 0:
            return redirect('admin_dashboard')

        balance_obj, _ = PointBalance.objects.get_or_create(user=user)
        balance_obj.student_balance = max(0, balance_obj.student_balance + delta)
        balance_obj.save()
        PointTransaction.objects.create(
            user=user,
            amount=delta,
            transaction_type=PointTransaction.TYPE_PURCHASE if delta > 0 else PointTransaction.TYPE_WITHDRAWAL,
            note=f"Admin student-point adjustment by {request.user.username}",
        )
    return redirect('admin_dashboard')

@staff_or_admin_role_required
def process_withdrawal(request, withdrawal_id):
    """引き出し申請を 支払済み or 却下 に更新する"""
    if request.method == 'POST':
        wr = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        action = request.POST.get('action')  # 'paid' or 'reject'

        if action == 'paid' and wr.status == WithdrawalRequest.STATUS_PENDING:
            wr.status = WithdrawalRequest.STATUS_PAID
            wr.admin_note = request.POST.get('admin_note', '')
            wr.processed_at = timezone.now()
            wr.save()

        elif action == 'reject' and wr.status == WithdrawalRequest.STATUS_PENDING:
            wr.status = WithdrawalRequest.STATUS_REJECTED
            wr.admin_note = request.POST.get('admin_note', '')
            wr.processed_at = timezone.now()
            wr.save()
            # 講師ポイントを返却
            balance, _ = PointBalance.objects.get_or_create(user=wr.user)
            balance.teacher_balance += wr.points
            balance.save()
            PointTransaction.objects.create(
                user=wr.user,
                amount=wr.points,
                transaction_type=PointTransaction.TYPE_SIGNUP_BONUS,
                note=f"Withdrawal rejected — points returned to teacher balance",
            )
    return redirect('admin_dashboard')


@staff_or_admin_role_required
def grant_initial_points_all(request):
    """PointBalanceを持っていない全ユーザーに初期ポイントを一括付与"""
    if request.method == 'POST':
        users_without_balance = User.objects.filter(point_balance__isnull=True)
        for user in users_without_balance:
            PointBalance.objects.create(user=user, student_balance=INITIAL_BONUS)
            PointTransaction.objects.create(
                user=user,
                amount=INITIAL_BONUS,
                transaction_type=PointTransaction.TYPE_SIGNUP_BONUS,
                note="Initial bonus (admin grant)",
            )
    return redirect('admin_dashboard')


@staff_or_admin_role_required
def grant_gold(request, user_id):
    """ユーザーに Gold メンバーシップを 30 日付与（申請承認 or 直接付与）"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        now = timezone.now()
        expires_at = now + timedelta(days=30)

        # 既存の membership があれば延長、なければ新規作成
        membership, created = GoldMembership.objects.get_or_create(
            user=user,
            defaults={'expires_at': expires_at},
        )
        if not created:
            # 既に active なら残り日数に +30日、期限切れなら今から30日
            base = max(membership.expires_at, now)
            membership.expires_at = base + timedelta(days=30)
            membership.save()

        # 対応する申請があれば承認済みに更新
        GoldSubscriptionRequest.objects.filter(
            user=user, status=GoldSubscriptionRequest.STATUS_PENDING
        ).update(
            status=GoldSubscriptionRequest.STATUS_ACTIVATED,
            processed_at=now,
        )

    return redirect('admin_dashboard')


@staff_or_admin_role_required
def revoke_gold(request, user_id):
    """ユーザーの Gold メンバーシップを即時失効する"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        now = timezone.now()

        GoldMembership.objects.filter(user=user).update(expires_at=now)
        GoldSubscriptionRequest.objects.filter(
            user=user, status=GoldSubscriptionRequest.STATUS_PENDING
        ).update(
            status=GoldSubscriptionRequest.STATUS_REJECTED,
            processed_at=now,
        )

    return redirect('admin_dashboard')


def _parse_cet_to_utc(date_str, time_str):
    """'YYYY-MM-DD' + 'HH:MM' (Europe/Zurich) → UTC-aware datetime"""
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    cet_dt = naive.replace(tzinfo=ZoneInfo('Europe/Zurich'))
    return cet_dt.astimezone(ZoneInfo('UTC'))


@staff_or_admin_role_required
def session_create(request):
    if request.method == 'POST':
        date_str  = request.POST.get('date', '')
        start_str = request.POST.get('start_time', '')
        end_str   = request.POST.get('end_time', '')
        try:
            start_utc = _parse_cet_to_utc(date_str, start_str)
            end_utc   = _parse_cet_to_utc(date_str, end_str)
        except ValueError:
            return redirect('admin_dashboard')
        UpcomingSession.objects.create(
            start_time     = start_utc,
            end_time       = end_utc,
            english_count  = int(request.POST.get('english_count',  0) or 0),
            french_count   = int(request.POST.get('french_count',   0) or 0),
            spanish_count  = int(request.POST.get('spanish_count',  0) or 0),
            japanese_count = int(request.POST.get('japanese_count', 0) or 0),
            note           = request.POST.get('note', '').strip(),
            is_published   = request.POST.get('is_published') == 'on',
        )
    return redirect('admin_dashboard')


@staff_or_admin_role_required
def session_edit(request, session_id):
    if request.method == 'POST':
        s = get_object_or_404(UpcomingSession, id=session_id)
        date_str  = request.POST.get('date', '')
        start_str = request.POST.get('start_time', '')
        end_str   = request.POST.get('end_time', '')
        try:
            s.start_time = _parse_cet_to_utc(date_str, start_str)
            s.end_time   = _parse_cet_to_utc(date_str, end_str)
        except ValueError:
            return redirect('admin_dashboard')
        s.english_count  = int(request.POST.get('english_count',  0) or 0)
        s.french_count   = int(request.POST.get('french_count',   0) or 0)
        s.spanish_count  = int(request.POST.get('spanish_count',  0) or 0)
        s.japanese_count = int(request.POST.get('japanese_count', 0) or 0)
        s.note           = request.POST.get('note', '').strip()
        s.is_published   = request.POST.get('is_published') == 'on'
        s.save()
    return redirect('admin_dashboard')


@staff_or_admin_role_required
def session_delete(request, session_id):
    if request.method == 'POST':
        get_object_or_404(UpcomingSession, id=session_id).delete()
    return redirect('admin_dashboard')
