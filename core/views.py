import random
from datetime import timedelta

from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import (
    LessonLanguage,
    StudentProfile,
    TutorProfile,
    QuickLessonRequest,
    QuickLessonMatch,
)


def home(request):
    return render(request, "core/home.html")


@login_required
def create_request(request):
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        lang_id = request.POST.get("language_id")
        language = get_object_or_404(LessonLanguage, id=lang_id)

        qlr = QuickLessonRequest.objects.create(
            student=student_profile,
            language=language,
            purpose="lesson",   # ← この1行を追加
        )

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
                meeting_url="https://example.com/dummy-room",
                price=5.0,
            )
            qlr.status = "matched"
            qlr.save()

            tutor.is_online = False
            tutor.save()

        return redirect("request_detail", request_id=qlr.id)

    languages = LessonLanguage.objects.all()
    return render(request, "core/create_request.html", {"languages": languages})



@login_required
def request_detail(request, request_id: int):
    qlr = get_object_or_404(
        QuickLessonRequest,
        id=request_id,
        student__user=request.user,
    )

    # すでにマッチがあるか確認
    match = QuickLessonMatch.objects.filter(request=qlr).first()

    # まだ waiting で、マッチが無い場合は「ここでもう一回マッチングを試す」
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

    return render(
        request,
        "core/tutor_dashboard.html",
        {"tutor": tutor_profile, "matches": matches},
    )


@login_required
def create_interview_request(request):
    """
    講師候補の5分面接リクエスト用。
    とりあえず動かすだけなら create_request のほぼコピペでOK。
    """
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        lang_id = request.POST.get("language_id")
        language = get_object_or_404(LessonLanguage, id=lang_id)

        # purpose='interview' で作る
        qlr = QuickLessonRequest.objects.create(
            student=student_profile,
            language=language,
            purpose="interview",
        )

        # 面接可能な講師（can_interview=True）だけを対象にする
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
                meeting_url="https://example.com/dummy-room/interview",  # 後でAPIで差し替え
                price=0.0,  # 面接なので無料想定
            )
            qlr.status = "matched"
            qlr.save()

            tutor.is_online = False
            tutor.save()

        return redirect("request_detail", request_id=qlr.id)

    languages = LessonLanguage.objects.all()
    return render(request, "core/create_interview_request.html", {"languages": languages})
