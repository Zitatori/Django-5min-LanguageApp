from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from core.models import QuickLessonMatch, PointBalance


class VideoRoomView(TemplateView):
    template_name = "video_room.html"


def video_room(request):
    return render(request, "video_room.html")


@login_required
def lesson_room(request, match_id: int):
    match = get_object_or_404(QuickLessonMatch, id=match_id)

    # 生徒は残高1pt以上ないと入室不可
    is_student = (request.user == match.request.student.user)
    if is_student:
        balance = PointBalance.objects.filter(user=request.user).first()
        if not balance or balance.balance < 1:
            return redirect('purchase_points')

    now = timezone.now()

    if request.user == match.request.student.user and not match.student_joined_at:
        match.student_joined_at = now

    if request.user == match.tutor.user and not match.tutor_joined_at:
        match.tutor_joined_at = now

    if match.student_joined_at and match.tutor_joined_at and not match.started_at:
        match.started_at = now
        match.end_at = now + timezone.timedelta(minutes=5)

    match.save()

    if match.started_at:
        remaining_seconds = max(0, int((match.end_at - now).total_seconds()))
    else:
        remaining_seconds = None

    if request.user == match.request.student.user:
        partner_name = match.tutor.user.username
    else:
        partner_name = match.request.student.user.username

    context = {
        "match": match,
        "remaining_seconds": remaining_seconds,
        "partner_name": partner_name,
        "partner_initial": partner_name[0].upper() if partner_name else "?",
    }

    return render(request, "core/lesson_room.html", context)