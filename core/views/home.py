from zoneinfo import ZoneInfo

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db.models import Count
from django.http import HttpResponseBadRequest, HttpResponseForbidden
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


@never_cache
def home(request):
    now = timezone.now()
    sessions_qs = (
        UpcomingSession.objects
        .filter(is_published=True, end_time__gt=now)
        .annotate(planned_count=Count('planned_students'))
        .order_by('start_time')[:10]
    )

    student = getattr(request.user, 'studentprofile', None) if request.user.is_authenticated else None
    planned = set(student.planned_sessions.values_list('pk', flat=True)) if student else set()
    sessions = []
    for session in sessions_qs:
        session.is_planned = session.pk in planned
        sessions.append(_session_display(session))

    return render(request, "core/home.html", {
        'can_plan_attendance': student is not None,
        'next_session':      sessions[0] if sessions else None,
        'other_sessions':    sessions[1:],
    })


def privacy(request):
    return render(request, "core/privacy.html")

@login_required
@require_POST
def session_attendance(request, session_id):
    student = getattr(request.user, 'studentprofile', None)
    if student is None:
        return HttpResponseForbidden()
    session = get_object_or_404(UpcomingSession, pk=session_id, is_published=True, end_time__gt=timezone.now())
    attending = request.POST.get('attending')
    if attending == 'yes':
        session.planned_students.add(student)
    elif attending == 'no':
        session.planned_students.remove(student)
    else:
        return HttpResponseBadRequest()
    return redirect('home')
