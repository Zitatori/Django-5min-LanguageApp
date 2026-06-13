import json
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField, Count
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage
from core.models import PointBalance, PointTransaction, WithdrawalRequest
from core.models import GoldMembership, GoldSubscriptionRequest
from datetime import timedelta

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
        .order_by('date_joined')
    )
    tutors = TutorProfile.objects.select_related('user').prefetch_related('languages').all()
    matches = QuickLessonMatch.objects.filter(
        student_joined_at__isnull=False,  # 実際に通話したものだけ
    ).select_related(
        'request__student__user',
        'request__language',
        'tutor__user',
    ).order_by('-started_at')

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

    no_balance_count = User.objects.filter(point_balance__isnull=True).count()
    withdrawal_requests = WithdrawalRequest.objects.select_related('user').order_by('-created_at')
    gold_requests = GoldSubscriptionRequest.objects.select_related('user').filter(
        status=GoldSubscriptionRequest.STATUS_PENDING
    )

    return render(request, 'core/admin_dashboard.html', {
        'users':               users,
        'users_count': users.count(),
        'tutors':              tutors,
        'matches':             matches,
        'languages':           languages,
        'user_matches_json':   user_matches_json,
        'no_balance_count':    no_balance_count,
        'withdrawal_requests': withdrawal_requests,
        'gold_requests':       gold_requests,
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
    """管理者がユーザーのポイント残高を直接セットする"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        try:
            new_balance = int(request.POST.get('balance', 0))
        except ValueError:
            return redirect('admin_dashboard')

        balance_obj, _ = PointBalance.objects.get_or_create(user=user)
        diff = new_balance - balance_obj.balance
        if diff != 0:
            balance_obj.balance = new_balance
            balance_obj.save()
            PointTransaction.objects.create(
                user=user,
                amount=diff,
                transaction_type=PointTransaction.TYPE_PURCHASE if diff > 0 else PointTransaction.TYPE_WITHDRAWAL,
                note=f"Admin adjustment by {request.user.username}",
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
            # ポイントを返却
            balance, _ = PointBalance.objects.get_or_create(user=wr.user)
            balance.balance        += wr.points
            balance.earned_balance += wr.points
            balance.save()
            PointTransaction.objects.create(
                user=wr.user,
                amount=wr.points,
                transaction_type=PointTransaction.TYPE_SIGNUP_BONUS,
                note=f"Withdrawal rejected — points returned",
            )
    return redirect('admin_dashboard')


@staff_or_admin_role_required
def grant_initial_points_all(request):
    """PointBalanceを持っていない全ユーザーに初期ポイントを一括付与"""
    if request.method == 'POST':
        users_without_balance = User.objects.filter(point_balance__isnull=True)
        for user in users_without_balance:
            PointBalance.objects.create(user=user, balance=INITIAL_BONUS)
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