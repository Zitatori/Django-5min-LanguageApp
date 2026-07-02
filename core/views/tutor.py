from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.models import LessonLanguage, TutorProfile, QuickLessonMatch
from django.http import JsonResponse


@login_required
def tutor_dashboard(request):
    tutor_profile, _ = TutorProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "go_online":
            # 通話中/入室待ちのマッチがある間は、手動操作でも待機状態に戻さない。
            tutor_profile.is_online = _active_match_for_tutor(tutor_profile) is None
            tutor_profile.last_ping_at = timezone.now()  # オンライン時は即座にping時刻を設定
        elif action == "go_offline":
            tutor_profile.is_online = False

        tutor_profile.save()

    matches = QuickLessonMatch.objects.filter(
        tutor=tutor_profile,
        student_joined_at__isnull=False,  # 実際に通話したものだけ
    ).select_related(
        "request",
        "request__student",
        "request__student__user",
        "request__language",
    ).order_by("-started_at")

    active_matches = QuickLessonMatch.objects.filter(
        tutor=tutor_profile,
    ).filter(
        Q(started_at__isnull=True) | Q(end_at__gt=timezone.now())
    ).select_related(
        "request",
        "request__student",
        "request__student__user",
        "request__language",
        "tutor",
        "tutor__user",
    ).order_by("-started_at")

    # 言語別の担当レッスン数
    lang_name_counts = dict(
        QuickLessonMatch.objects.filter(tutor=tutor_profile)
        .values("request__language__name")
        .annotate(cnt=Count("id"))
        .values_list("request__language__name", "cnt")
    )
    total_lessons_taught = sum(lang_name_counts.values())
    # 全言語対応: DBの言語を順番に並べて (lang, count) のリストに
    lang_lesson_stats = [
        (lang, lang_name_counts[lang.name])
        for lang in LessonLanguage.objects.all()
        if lang.name in lang_name_counts
    ]

    return render(
        request,
        "core/tutor_dashboard.html",
        {
            "tutor": tutor_profile,
            "active_matches": active_matches,
            "matches": matches,
            "lang_lesson_stats": lang_lesson_stats,
            "total_lessons_taught": total_lessons_taught,
        },
    )
ONLINE_TIMEOUT_SECONDS = 1800  # 30分以内の ping がないとオフライン扱い（スマホスリープ対策）


def _active_match_for_tutor(tutor_profile, now=None):
    now = now or timezone.now()
    return QuickLessonMatch.objects.filter(
        tutor=tutor_profile,
    ).filter(
        Q(started_at__isnull=True) | Q(end_at__gt=now)
    ).first()


@login_required
def tutor_match_status(request):
    """ポーリング兼ハートビート。呼ばれるたびに last_ping_at を更新。"""
    from django.urls import reverse
    now = timezone.now()
    tutor_profile = TutorProfile.objects.get(user=request.user)

    # マッチ中かどうかを先に確認する（is_online の上書きより前）
    active_match = _active_match_for_tutor(tutor_profile, now=now)

    if active_match:
        # レッスン中: is_online=False のまま維持し、last_ping_at だけ更新
        # ← ここで is_online=True に戻すとダブルブッキングが発生する
        TutorProfile.objects.filter(pk=tutor_profile.pk).update(last_ping_at=now)
        return JsonResponse({
            "matched": True,
            "room_url": reverse("lesson_room", args=[active_match.id])
        })

    # マッチなし: ハートビートで is_online=True を維持（スマホスリープ等からの復旧も兼ねる）
    TutorProfile.objects.filter(pk=tutor_profile.pk).update(
        is_online=True, last_ping_at=now
    )
    return JsonResponse({"matched": False})


@login_required
@require_POST
def tutor_set_offline(request):
    """チューターがタブを閉じたときなどに sendBeacon で叩くエンドポイント。"""
    TutorProfile.objects.filter(user=request.user).update(is_online=False)
    return JsonResponse({"ok": True})
