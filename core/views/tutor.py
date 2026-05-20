from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from core.models import TutorProfile, QuickLessonMatch


@login_required
def tutor_dashboard(request):
    tutor_profile, _ = TutorProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "go_online":
            tutor_profile.is_online = True
        elif action == "go_offline":
            tutor_profile.is_online = False

        tutor_profile.save()

    matches = QuickLessonMatch.objects.filter(
        tutor=tutor_profile
    ).select_related(
        "request",
        "request__student",
        "request__student__user",
        "request__language",
    ).order_by("-started_at")

    active_matches = QuickLessonMatch.objects.filter(
        tutor=tutor_profile,
        end_at__gt=timezone.now()
    ).select_related(
        "request",
        "request__student",
        "request__student__user",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    return render(
        request,
        "core/tutor_dashboard.html",
        {
            "tutor": tutor_profile,
            "active_matches": active_matches,
            "matches": matches,
        },
    )