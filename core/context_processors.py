from django.utils import timezone
from core.tutor_access import can_access_tutor_dashboard


def gold_status(request):
    """全テンプレートで {{ is_gold }}, {{ gold_expires_at }}, {{ nav_points }} を利用可能にする"""
    if not request.user.is_authenticated:
        return {'is_gold': False, 'gold_expires_at': None, 'nav_points': None}
    try:
        membership = request.user.gold_membership
        active = membership.expires_at > timezone.now()
    except Exception:
        active = False

    if active:
        nav_points = '∞'
    else:
        try:
            nav_points = request.user.point_balance.student_balance
        except Exception:
            nav_points = None

    return {
        'is_gold': active,
        'can_access_tutor_dashboard': can_access_tutor_dashboard(request.user),
        'gold_expires_at': membership.expires_at if active else None,
        'nav_points': nav_points,
    }
