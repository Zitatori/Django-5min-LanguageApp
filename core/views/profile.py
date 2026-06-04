from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from core.models import PointBalance, PointTransaction, WithdrawalRequest

MIN_WITHDRAWAL_PTS = 50  # 最低引き出しポイント


def _get_or_create_balance(user):
    balance, _ = PointBalance.objects.get_or_create(user=user, defaults={'balance': 0})
    return balance


@login_required
def profile(request):
    balance      = _get_or_create_balance(request.user)
    transactions = PointTransaction.objects.filter(user=request.user)[:20]
    pending_withdrawal = WithdrawalRequest.objects.filter(
        user=request.user, status=WithdrawalRequest.STATUS_PENDING
    ).first()

    # 引き出し可能額 = 講師として稼いだ分 と 総残高 の小さい方
    withdrawable = min(balance.earned_balance, balance.balance)

    return render(request, 'core/profile.html', {
        'balance':            balance,
        'withdrawable':       withdrawable,
        'transactions':       transactions,
        'pending_withdrawal': pending_withdrawal,
        'min_withdrawal':     MIN_WITHDRAWAL_PTS,
        'can_withdraw':       (
            hasattr(request.user, 'tutorprofile')
            and withdrawable >= MIN_WITHDRAWAL_PTS
            and not pending_withdrawal
        ),
        'withdrawal_currencies': WithdrawalRequest.CURRENCY_CHOICES,
        'withdrawal_methods':    WithdrawalRequest.METHOD_CHOICES,
    })


@login_required
def request_withdrawal(request):
    if request.method != 'POST':
        return redirect('profile')

    balance = _get_or_create_balance(request.user)

    try:
        points = int(request.POST.get('points', 0))
    except ValueError:
        return redirect('profile')

    # バリデーション（引き出し可能額 = earned と balance の小さい方）
    withdrawable = min(balance.earned_balance, balance.balance)
    if (points < MIN_WITHDRAWAL_PTS
            or withdrawable < points
            or not hasattr(request.user, 'tutorprofile')):
        return redirect('profile')

    # 既に申請中なら重複させない
    if WithdrawalRequest.objects.filter(
        user=request.user, status=WithdrawalRequest.STATUS_PENDING
    ).exists():
        return redirect('profile')

    # ポイントを予約（earned_balance & balance 両方から引く）
    balance.earned_balance -= points
    balance.balance        -= points
    balance.save()

    PointTransaction.objects.create(
        user=request.user,
        amount=-points,
        transaction_type=PointTransaction.TYPE_WITHDRAWAL,
        note="Withdrawal request submitted",
    )

    WithdrawalRequest.objects.create(
        user=request.user,
        points=points,
        currency=request.POST.get('currency', 'EUR'),
        payment_method=request.POST.get('payment_method', 'wise'),
        payment_details=request.POST.get('payment_details', ''),
    )

    return redirect('profile')


@login_required
def purchase_points(request):
    TIERS = [
        {'points': 10,  'price_jpy': 1000},
        {'points': 50,  'price_jpy': 4500},
        {'points': 100, 'price_jpy': 8000},
    ]
    balance = _get_or_create_balance(request.user)
    return render(request, 'core/purchase_points.html', {
        'tiers':   TIERS,
        'balance': balance,
    })
