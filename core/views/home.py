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
        'jst_start': jst_start,
        'jst_end':   jst_end,
        'cet_start': cet_start,
        'cet_end':   cet_end,
        'cet_abbrev': cet_start.strftime('%Z'),  # CET / CEST
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
        'upcoming_sessions': sessions,
    })


def privacy(request):
    return render(request, "core/privacy.html")