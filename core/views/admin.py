from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage
from core.models import PointBalance, PointTransaction, WithdrawalRequest

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
        .select_related('userprofile', 'tutorprofile', 'point_balance')
        .prefetch_related('tutorprofile__languages')
        .order_by('date_joined')
    )
    tutors = TutorProfile.objects.select_related('user').prefetch_related('languages').all()
    matches = QuickLessonMatch.objects.select_related(
        'request__student__user',
        'request__language',
        'tutor__user',
    ).order_by('-started_at')

    languages = LessonLanguage.objects.all()

    no_balance_count = User.objects.filter(point_balance__isnull=True).count()
    withdrawal_requests = WithdrawalRequest.objects.select_related('user').order_by('-created_at')

    return render(request, 'core/admin_dashboard.html', {
        'users':               users,
        'users_count': users.count(),
        'tutors':              tutors,
        'matches':             matches,
        'languages':           languages,
        'no_balance_count':    no_balance_count,
        'withdrawal_requests': withdrawal_requests,
    })

@staff_or_admin_role_required
def update_tutor_languages(request, tutor_id):
    if request.method == 'POST':
        tutor = get_object_or_404(TutorProfile, id=tutor_id)
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