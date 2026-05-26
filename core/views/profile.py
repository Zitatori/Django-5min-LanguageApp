from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from core.models import PointBalance, PointTransaction


def _get_or_create_balance(user):
    balance, _ = PointBalance.objects.get_or_create(user=user, defaults={'balance': 0})
    return balance


@login_required
def profile(request):
    balance = _get_or_create_balance(request.user)
    transactions = PointTransaction.objects.filter(user=request.user)[:20]
    return render(request, 'core/profile.html', {
        'balance': balance,
        'transactions': transactions,
    })


@login_required
def purchase_points(request):
    TIERS = [
        {'points': 10,  'price_jpy': 1000,  'label': '10 pt'},
        {'points': 50,  'price_jpy': 4500,  'label': '50 pt'},
        {'points': 100, 'price_jpy': 8000,  'label': '100 pt'},
    ]
    balance = _get_or_create_balance(request.user)
    return render(request, 'core/purchase_points.html', {
        'tiers': TIERS,
        'balance': balance,
    })
