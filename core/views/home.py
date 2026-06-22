from zoneinfo import ZoneInfo

from django.shortcuts import render
from django.utils import timezone

from core.models import UpcomingSession


def home(request):
    now = timezone.now()
    sessions_qs = (
        UpcomingSession.objects
        .filter(is_published=True, start_time__gt=now)
        .order_by('start_time')[:5]
    )

    sessions = []
    for s in sessions_qs:
        tz = ZoneInfo(s.timezone)
        local_dt = s.start_time.astimezone(tz)
        sessions.append({
            'obj': s,
            'local_dt': local_dt,
            'tz_abbrev': local_dt.strftime('%Z'),   # JST / CET / CEST
        })

    return render(request, "core/home.html", {
        'next_session':      sessions[0] if sessions else None,
        'upcoming_sessions': sessions,
    })


def privacy(request):
    return render(request, "core/privacy.html")