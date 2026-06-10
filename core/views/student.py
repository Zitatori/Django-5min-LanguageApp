import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import (
    LessonLanguage,
    StudentProfile,
    TutorProfile,
    QuickLessonRequest,
    QuickLessonMatch,
)

ONLINE_TIMEOUT_SECONDS = 1800     # tutor.py と合わせる（30分）スマホスリープ対策
CONSECUTIVE_WAIT_SECONDS = 60    # 連続マッチを禁じる猶予期間（1分）


def _get_consecutive_exclude_ids(student_profile):
    """マッチング用: 60秒以内に同じペアで連続マッチするのを防ぐ除外セット。
    - 60秒を過ぎていれば同じ人とも再マッチ可能
    - 別の人とは即マッチ可能（除外されない）
    """
    now = timezone.now()
    cutoff = now - timedelta(seconds=CONSECUTIVE_WAIT_SECONDS)
    exclude_ids = set()

    # 生徒側: 60秒以内に終わった直前マッチの相手を除外
    last = (
        QuickLessonMatch.objects
        .filter(request__student=student_profile, end_at__gt=cutoff)
        .order_by("-started_at")
        .values("tutor_id")
        .first()
    )
    if last:
        exclude_ids.add(last["tutor_id"])

    # チューター側: 60秒以内の直前マッチがこの生徒だったチューターを除外
    latest_student_sq = (
        QuickLessonMatch.objects
        .filter(tutor=OuterRef("pk"))
        .order_by("-started_at")
        .values("request__student_id")[:1]
    )
    latest_end_sq = (
        QuickLessonMatch.objects
        .filter(tutor=OuterRef("pk"))
        .order_by("-started_at")
        .values("end_at")[:1]
    )
    ids = (
        TutorProfile.objects
        .annotate(
            last_student_id=Subquery(latest_student_sq),
            last_end_at=Subquery(latest_end_sq),
        )
        .filter(
            last_student_id=student_profile.pk,
            last_end_at__gt=cutoff,
        )
        .values_list("pk", flat=True)
    )
    exclude_ids.update(ids)
    return exclude_ids


def _get_display_exclude_ids(student_profile):
    """表示用（オンライン人数カウント）: 猶予期間中のみ除外。
    end_at + CONSECUTIVE_WAIT_SECONDS が過ぎたチューターは表示に戻す。
    """
    now = timezone.now()
    # この時刻より後に end_at があるマッチ = まだ猶予期間内
    hide_until_cutoff = now - timedelta(seconds=CONSECUTIVE_WAIT_SECONDS)
    exclude_ids = set()

    # 生徒側: 直前マッチが猶予期間内なら除外
    last = (
        QuickLessonMatch.objects
        .filter(request__student=student_profile)
        .order_by("-started_at")
        .first()
    )
    if last and last.end_at > hide_until_cutoff:
        exclude_ids.add(last.tutor_id)

    # チューター側: 直前マッチがこの生徒で猶予期間内なら除外
    latest_student_sq = (
        QuickLessonMatch.objects
        .filter(tutor=OuterRef("pk"))
        .order_by("-started_at")
        .values("request__student_id")[:1]
    )
    latest_end_sq = (
        QuickLessonMatch.objects
        .filter(tutor=OuterRef("pk"))
        .order_by("-started_at")
        .values("end_at")[:1]
    )
    ids = (
        TutorProfile.objects
        .annotate(
            last_student_id=Subquery(latest_student_sq),
            last_end_at=Subquery(latest_end_sq),
        )
        .filter(
            last_student_id=student_profile.pk,
            last_end_at__gt=hide_until_cutoff,
        )
        .values_list("pk", flat=True)
    )
    exclude_ids.update(ids)
    return exclude_ids


def active_tutors_qs(language=None):
    """実際にオンライン中（5分以内に ping あり）のチュータークエリセット。
    last_ping_at が未設定（None）の場合は ping タイムアウトを適用しない。
    """
    cutoff = timezone.now() - timedelta(seconds=ONLINE_TIMEOUT_SECONDS)
    qs = TutorProfile.objects.filter(is_online=True).filter(
        Q(last_ping_at__isnull=True) | Q(last_ping_at__gte=cutoff)
    )
    if language:
        qs = qs.filter(languages=language)
    return qs.distinct()


@login_required
def create_request(request):
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    # Student ページに来たら自分の Tutor をオフラインに
    TutorProfile.objects.filter(user=request.user, is_online=True).update(is_online=False)

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

        tutors_qs = active_tutors_qs(language=language)

        # 連続マッチ防止（60秒以内の同一ペアのみ除外）
        exclude_ids = _get_consecutive_exclude_ids(student_profile)
        if exclude_ids:
            filtered_qs = tutors_qs.exclude(pk__in=exclude_ids)
            if filtered_qs.exists():
                # 別の候補がいる → すぐマッチ
                tutors_qs = filtered_qs
            else:
                # 同一ペアしかいない → 60秒経過していればマッチ許可、でなければ待機
                last_match = (
                    QuickLessonMatch.objects
                    .filter(request__student=student_profile)
                    .order_by("-end_at")
                    .first()
                )
                elapsed_since_end = (
                    (timezone.now() - last_match.end_at).total_seconds()
                    if last_match and last_match.end_at else CONSECUTIVE_WAIT_SECONDS
                )
                if elapsed_since_end < CONSECUTIVE_WAIT_SECONDS:
                    tutors_qs = tutors_qs.none()

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

        # マッチできる相手がいない（前回の相手は60秒除外中）→ リクエストを破棄してホームへ戻す
        qlr.delete()
        return redirect("create_request")

    languages = LessonLanguage.objects.all()
    matches = QuickLessonMatch.objects.filter(
        request__student__user=request.user,
        student_joined_at__isnull=False,  # 実際に通話したものだけ
    ).select_related(
        "request",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    # 表示用（オンラインカウント）: 猶予期間中のみ除外
    consecutive_exclude = _get_display_exclude_ids(student_profile)

    # 言語別の受講済みレッスン数（通話成立分のみ）
    lang_lesson_counts = dict(
        QuickLessonMatch.objects.filter(
            request__student=student_profile,
            student_joined_at__isnull=False,
        )
        .values("request__language_id")
        .annotate(cnt=Count("id"))
        .values_list("request__language_id", "cnt")
    )

    languages_with_count = []
    for lang in languages:
        qs = active_tutors_qs(language=lang)
        if consecutive_exclude:
            qs = qs.exclude(pk__in=consecutive_exclude)
        online_count = qs.count()
        lesson_count = lang_lesson_counts.get(lang.id, 0)
        languages_with_count.append((lang, online_count, lesson_count))

    total_lessons = sum(lang_lesson_counts.values())

    return render(request, "core/create_request.html", {
        "languages_with_count": languages_with_count,
        "matches": matches,
        "total_lessons": total_lessons,
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
        now = timezone.now()
        tutors_qs = active_tutors_qs(language=qlr.language)

        # 60秒以内の同一ペアを除外して別の相手を優先
        exclude_ids = _get_consecutive_exclude_ids(qlr.student)
        if exclude_ids:
            filtered_qs = tutors_qs.exclude(pk__in=exclude_ids)
            tutors_qs = filtered_qs if filtered_qs.exists() else tutors_qs.none()

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
        {
            "request_obj": qlr,
            "match": match,
        },
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

@login_required
def student_online_counts(request):
    """言語ごとのオンライン講師数をJSONで返す（生徒側ポーリング用）"""
    from django.http import JsonResponse
    student_profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    # 表示用: 猶予期間（60秒）を過ぎたら除外を解除して表示に戻す
    display_exclude = _get_display_exclude_ids(student_profile)
    languages = LessonLanguage.objects.all()
    data = {}
    for lang in languages:
        qs = active_tutors_qs(language=lang)
        if display_exclude:
            qs = qs.exclude(pk__in=display_exclude)
        data[str(lang.id)] = qs.count()
    return JsonResponse(data)


def student_history(request):
    matches = QuickLessonMatch.objects.filter(
        request__student__user=request.user,
        student_joined_at__isnull=False,  # 実際に通話したものだけ
    ).select_related(
        "request",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    return render(request, "core/student_history.html", {
        "matches": matches,
    })