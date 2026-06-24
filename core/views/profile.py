from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from core.models import PointBalance, PointTransaction, WithdrawalRequest
from core.models import GoldMembership, GoldSubscriptionRequest

MIN_WITHDRAWAL_PTS = 20  # 最低引き出しポイント
FEE_THRESHOLD      = 50  # これ以上は手数料無料
WITHDRAWAL_FEE     = 5   # 手数料


def _get_or_create_balance(user):
    balance, _ = PointBalance.objects.get_or_create(user=user, defaults={'balance': 0})
    return balance


def calc_withdrawal_fee(points):
    return 0 if points >= FEE_THRESHOLD else WITHDRAWAL_FEE


@login_required
def profile(request):
    balance      = _get_or_create_balance(request.user)
    transactions = PointTransaction.objects.filter(user=request.user)[:20]
    pending_withdrawal = WithdrawalRequest.objects.filter(
        user=request.user, status=WithdrawalRequest.STATUS_PENDING
    ).first()

    # 引き出し可能額 = 講師として稼いだ分 と 総残高 の小さい方
    withdrawable = min(balance.earned_balance, balance.balance)
    is_tutor     = hasattr(request.user, 'tutorprofile')

    # Gold 申請中かどうか
    gold_request_pending = GoldSubscriptionRequest.objects.filter(
        user=request.user, status=GoldSubscriptionRequest.STATUS_PENDING
    ).exists()

    return render(request, 'core/profile.html', {
        'balance':            balance,
        'withdrawable':       withdrawable,
        'transactions':       transactions,
        'pending_withdrawal': pending_withdrawal,
        'min_withdrawal':     MIN_WITHDRAWAL_PTS,
        'fee_threshold':      FEE_THRESHOLD,
        'withdrawal_fee':     WITHDRAWAL_FEE,
        'can_withdraw':       (
            is_tutor
            and withdrawable >= MIN_WITHDRAWAL_PTS
            and not pending_withdrawal
        ),
        'withdrawal_currencies': WithdrawalRequest.CURRENCY_CHOICES,
        'withdrawal_methods':    WithdrawalRequest.METHOD_CHOICES,
        'gold_request_pending':  gold_request_pending,
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

    fee = calc_withdrawal_fee(points)

    # ポイントを予約（earned_balance & balance 両方から引く）
    balance.earned_balance -= points
    balance.balance        -= points
    balance.save()

    PointTransaction.objects.create(
        user=request.user,
        amount=-points,
        transaction_type=PointTransaction.TYPE_WITHDRAWAL,
        note=f"Withdrawal request submitted (fee: {fee}pt, net: {points - fee}pt)",
    )

    WithdrawalRequest.objects.create(
        user=request.user,
        points=points,
        fee=fee,
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


@login_required
def request_gold(request):
    """ゴールド会員申請（重複防止、申請中は再送不可）"""
    if request.method != 'POST':
        return redirect('profile')

    # 既にアクティブな Gold メンバーなら不要
    try:
        membership = request.user.gold_membership
        if membership.is_active:
            return redirect('profile')
    except Exception:
        pass

    # 申請中なら重複させない
    if GoldSubscriptionRequest.objects.filter(
        user=request.user, status=GoldSubscriptionRequest.STATUS_PENDING
    ).exists():
        return redirect('profile')

    GoldSubscriptionRequest.objects.create(user=request.user)
    return redirect('profile')
