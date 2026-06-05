from django.utils import timezone


def gold_status(request):
    """全テンプレートで {{ is_gold }} と {{ gold_expires_at }} を利用可能にする"""
    if not request.user.is_authenticated:
        return {'is_gold': False, 'gold_expires_at': None}
    try:
        membership = request.user.gold_membership
        active = membership.expires_at > timezone.now()
        return {
            'is_gold': active,
            'gold_expires_at': membership.expires_at if active else None,
        }
    except Exception:
        return {'is_gold': False, 'gold_expires_at': None}
