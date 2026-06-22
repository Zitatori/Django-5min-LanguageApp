from zoneinfo import ZoneInfo

from django.shortcuts import render
from django.utils import timezone

from core.models import UpcomingSession

JST = ZoneInfo('Asia/Tokyo')
CET = ZoneInfo('Europe/Zurich')


def _session_display(s):
    jst_start = s.start_time.astimezone(JST)
    jst_end   = s.end_time.astimezone(JST)
    cet_start = s.start_time.astimezone(CET)
    cet_end   = s.end_time.astimezone(CET)
    return {
        'obj': s,
        # datetime.date オブジェクト（タイムゾーン変換なし）→ テンプレートの date フィルタで曜日・月名を i18n 表示
        'jst_date':     jst_start.date(),
        # 時刻は strftime で事前フォーマット（テンプレートフィルタが CET に変換するのを防ぐ）
        'jst_time':     jst_start.strftime('%H:%M'),
        'jst_end_time': jst_end.strftime('%H:%M'),
        'cet_time':     cet_start.strftime('%H:%M'),
        'cet_end_time': cet_end.strftime('%H:%M'),
    }


def home(request):
    now = timezone.now()
    sessions_qs = (
        UpcomingSession.objects
        .filter(is_published=True, end_time__gt=now)
        .order_by('start_time')[:5]
    )

    sessions = [_session_display(s) for s in sessions_qs]

    return render(request, "core/home.html", {
        'next_session':      sessions[0] if sessions else None,
        'other_sessions':    sessions[1:],
    })


def privacy(request):
    return render(request, "core/privacy.html")