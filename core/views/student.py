import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import (
    LessonLanguage,
    StudentProfile,
    TutorProfile,
    QuickLessonRequest,
    QuickLessonMatch,
)


@login_required
def create_request(request):
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        lang_id = request.POST.get("language_id")
        language = get_object_or_404(LessonLanguage, id=lang_id)

        qlr = QuickLessonRequest.objects.create(
            student=student_profile,
            language=language,
            purpose="lesson",
        )

        if settings.DEBUG:
            demo_user, _ = User.objects.get_or_create(
                username="demo_tutor",
                defaults={"email": "demo_tutor@example.com"},
            )
            tutor_profile, _ = TutorProfile.objects.get_or_create(user=demo_user)

            now = timezone.now()
            QuickLessonMatch.objects.create(
                request=qlr,
                tutor=tutor_profile,
                started_at=now,
                end_at=now + timedelta(minutes=5),
                price=5.0,
            )

            qlr.status = "matched"
            qlr.save()

            return redirect("request_detail", request_id=qlr.id)

        tutors_qs = TutorProfile.objects.filter(
            is_online=True,
            languages=language,
        ).distinct()

        if tutors_qs.exists():
            tutor = random.choice(list(tutors_qs))
            now = timezone.now()

            QuickLessonMatch.objects.create(
                request=qlr,
                tutor=tutor,
                started_at=now,
                end_at=now + timedelta(minutes=5),
                price=5.0,
            )

            qlr.status = "matched"
            qlr.save()

            tutor.is_online = False
            tutor.save()

        return redirect("request_detail", request_id=qlr.id)

    languages = LessonLanguage.objects.all()
    matches = QuickLessonMatch.objects.filter(
        request__student__user=request.user
    ).select_related(
        "request",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    languages_with_count = []
    for lang in languages:
        count = TutorProfile.objects.filter(is_online=True, languages=lang).count()
        languages_with_count.append((lang, count))

    return render(request, "core/create_request.html", {
        "languages_with_count": languages_with_count,
        "matches": matches,
    })

@login_required
def request_detail(request, request_id: int):
    qlr = get_object_or_404(
        QuickLessonRequest,
        id=request_id,
        student__user=request.user,
    )

    match = QuickLessonMatch.objects.filter(request=qlr).first()

    if qlr.status == "waiting" and match is None:
        tutors_qs = TutorProfile.objects.filter(
            is_online=True,
            languages=qlr.language,
        ).distinct()

        if tutors_qs.exists():
            tutor = random.choice(list(tutors_qs))
            now = timezone.now()

            match = QuickLessonMatch.objects.create(
                request=qlr,
                tutor=tutor,
                started_at=now,
                end_at=now + timedelta(minutes=5),
                meeting_url="https://example.com/dummy-room",
                price=5.0,
            )

            qlr.status = "matched"
            qlr.save()

            tutor.is_online = False
            tutor.save()

    return render(
        request,
        "core/request_detail.html",
        {"request_obj": qlr, "match": match},
    )


@login_required
def create_interview_request(request):
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        lang_id = request.POST.get("language_id")
        language = get_object_or_404(LessonLanguage, id=lang_id)

        qlr = QuickLessonRequest.objects.create(
            student=student_profile,
            language=language,
            purpose="interview",
        )

        tutors_qs = TutorProfile.objects.filter(
            is_online=True,
            can_interview=True,
            languages=language,
        ).distinct()

        if tutors_qs.exists():
            tutor = random.choice(list(tutors_qs))
            now = timezone.now()

            QuickLessonMatch.objects.create(
                request=qlr,
                tutor=tutor,
                started_at=now,
                end_at=now + timedelta(minutes=5),
                meeting_url="https://example.com/dummy-room/interview",
                price=0.0,
            )

            qlr.status = "matched"
            qlr.save()

            tutor.is_online = False
            tutor.save()

        return redirect("request_detail", request_id=qlr.id)

    languages = LessonLanguage.objects.all()
    return render(request, "core/create_interview_request.html", {"languages": languages})

def student_history(request):
    matches = QuickLessonMatch.objects.filter(
        request__student__user=request.user
    ).select_related(
        "request",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    return render(request, "core/student_history.html", {
        "matches": matches,
    })