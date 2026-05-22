from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.generic import TemplateView

from core.models import QuickLessonMatch


class VideoRoomView(TemplateView):
    template_name = "video_room.html"


def video_room(request):
    return render(request, "video_room.html")


@login_required
def lesson_room(request, match_id: int):
    match = get_object_or_404(QuickLessonMatch, id=match_id)

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

    context = {
        "match": match,
        "remaining_seconds": remaining_seconds,
    }

    return render(request, "core/lesson_room.html", context)