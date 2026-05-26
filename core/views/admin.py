from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage
from core.models import PointBalance, PointTransaction

INITIAL_BONUS = 10

@staff_member_required
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

    # ボーナス未付与のユーザー数（バナー表示用）
    no_balance_count = User.objects.filter(point_balance__isnull=True).count()

    return render(request, 'core/admin_dashboard.html', {
        'users': users,
        'tutors': tutors,
        'matches': matches,
        'languages': languages,
        'no_balance_count': no_balance_count,
    })

@staff_member_required
def update_tutor_languages(request, tutor_id):
    if request.method == 'POST':
        tutor = get_object_or_404(TutorProfile, id=tutor_id)
        lang_ids = request.POST.getlist('languages')
        tutor.languages.set(lang_ids)
        return redirect('admin_dashboard')

@staff_member_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:
            user.delete()
    return redirect('admin_dashboard')

@staff_member_required
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

@staff_member_required
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