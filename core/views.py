from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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

        # レッスンリクエストを作成
        qlr = QuickLessonRequest.objects.create(
            student=student_profile,
            language=language,
            purpose="lesson",
        )

        # ★ テスト用：DEBUG のときは強制的にダミー講師とマッチさせる ★
        if settings.DEBUG:
            # demo_tutor というユーザーを自動で作る（なければ）
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

            # そのまま「マッチ済み画面」に飛ばす
            return redirect("request_detail", request_id=qlr.id)

        # ↓↓↓ ここから下は、将来ちゃんと講師探すモード用（今はほぼ通らない）

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

    # ★ 追加：ダミー履歴（DBが空のときだけ表示）
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
                "language": "Français",
                "partner": "Mike",
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
                "language": "Español",
                "partner": "Aika",
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
            },{
                "started_at": timezone.now() - timedelta(days=1, hours=2),
                "language": "日本語",
                "partner": "Mike",
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
            "dummy_matches": dummy_matches,  # ← これが必要
        },
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

        # 本番（or DEBUGでも後で本物にしたい場合）に使うDB取得
        matches = QuickLessonMatch.objects.filter(
            tutor=tutor_profile
        ).order_by("-started_at")[:20]

        # ★ フェイク履歴：DB未実装でも「それっぽく表示」したい用
        fake_history = []
        if settings.DEBUG and not matches.exists():
            fake_history = [
                {
                    "started_at": timezone.now() - timedelta(hours=3),
                    "language": "French",
                    "partner": "guest_104",
                    "purpose": "lesson",
                    "status": "ended",
                },
                {
                    "started_at": timezone.now() - timedelta(days=1, hours=2),
                    "language": "English",
                    "partner": "guest_087",
                    "purpose": "interview",
                    "status": "ended",
                },
            ]

        return render(
            request,
            "core/tutor_dashboard.html",
            {
                "tutor": tutor_profile,
                "matches": matches,
                "fake_history": fake_history,  # ← 追加
            },
        )

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


@login_required
def lesson_room(request, match_id: int):
    """
    5分レッスン用のシンプルなルーム画面。
    今はタイマーだけ。ビデオはこれから。
    """
    match = get_object_or_404(QuickLessonMatch, id=match_id)

    # 5分制限用：残り秒数を計算
    now = timezone.now()
    remaining_seconds = max(0, int((match.end_at - now).total_seconds()))

    context = {
        "match": match,
        "remaining_seconds": remaining_seconds,
    }
    return render(request, "core/lesson_room.html", context)
