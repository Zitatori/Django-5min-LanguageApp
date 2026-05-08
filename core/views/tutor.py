from datetime import timedelta

from django.conf import settings
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
    ).order_by("-started_at")[:20]

    dummy_matches = []

    if settings.DEBUG and not matches.exists():
        dummy_matches = [
            {
                "started_at": timezone.now() - timedelta(hours=3),
                "language": "Français",
                "partner": "Yuna",
                "purpose": "lesson",
                "status": "ended",
                "price": 5.0,
            },
            {
                "started_at": timezone.now() - timedelta(days=1, hours=2),
                "language": "Español",
                "partner": "Aika",
                "purpose": "interview",
                "status": "ended",
                "price": 0.0,
            },
            {
                "started_at": timezone.now() - timedelta(days=1, hours=2),
                "language": "日本語",
                "partner": "Jose",
                "purpose": "interview",
                "status": "ended",
                "price": 0.0,
            },
            {
                "started_at": timezone.now() - timedelta(days=1, hours=2),
                "language": "English",
                "partner": "Kani",
                "purpose": "interview",
                "status": "ended",
                "price": 0.0,
            },
        ]

    return render(
        request,
        "core/tutor_dashboard.html",
        {
            "tutor": tutor_profile,
            "matches": matches,
            "dummy_matches": dummy_matches,
        },
    )