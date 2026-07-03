from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from core.models import QuickLessonMatch, TutorProfile, PointBalance, GoldMembership
from django.utils import timezone as tz


class VideoRoomView(TemplateView):
    template_name = "video_room.html"


def video_room(request):
    return render(request, "video_room.html")


@login_required
def lesson_room(request, match_id: int):
    match = get_object_or_404(QuickLessonMatch, id=match_id)

    # 生徒は残高1pt以上ないと入室不可（Gold会員は免除）
    is_student = (request.user == match.request.student.user)
    if is_student:
        is_gold = False
        try:
            m = request.user.gold_membership
            is_gold = m.expires_at > tz.now()
        except Exception:
            pass

        if not is_gold:
            balance = PointBalance.objects.filter(user=request.user).first()
            if not balance or balance.student_balance < 1:
                return redirect('purchase_points')

    now = timezone.now()

    # 各フィールドを個別にアトミック更新（同時入室による上書きを防ぐ）
    if request.user == match.request.student.user and not match.student_joined_at:
        QuickLessonMatch.objects.filter(pk=match.pk, student_joined_at__isnull=True).update(
            student_joined_at=now
        )
        match.refresh_from_db()

    if request.user == match.tutor.user and not match.tutor_joined_at:
        TutorProfile.objects.filter(pk=match.tutor.pk).update(is_online=False)
        QuickLessonMatch.objects.filter(pk=match.pk, tutor_joined_at__isnull=True).update(
            tutor_joined_at=now
        )
        match.refresh_from_db()
    elif request.user == match.tutor.user:
        TutorProfile.objects.filter(pk=match.tutor.pk).update(is_online=False)

    if match.student_joined_at and match.tutor_joined_at and not match.started_at:
        QuickLessonMatch.objects.filter(pk=match.pk, started_at__isnull=True).update(
            started_at=now,
            end_at=now + timezone.timedelta(minutes=5),
        )
        match.refresh_from_db()

    if match.started_at:
        remaining_seconds = max(0, int((match.end_at - now).total_seconds()))
    else:
        remaining_seconds = None

    if request.user == match.request.student.user:
        partner_user = match.tutor.user
    else:
        partner_user = match.request.student.user

    partner_name = partner_user.username
    if partner_user.is_superuser:
        partner_badge = "dev"
    elif partner_user.is_staff:
        partner_badge = "admin"
    else:
        partner_badge = None
        try:
            gm = partner_user.gold_membership
            if gm.expires_at > tz.now():
                partner_badge = "gold"
        except Exception:
            pass

    context = {
        "match": match,
        "remaining_seconds": remaining_seconds,
        "timer_end_at": match.end_at if match.student_joined_at and match.tutor_joined_at else None,
        "after_lesson_url": reverse('lesson_rating', args=[match.id]) if is_student else reverse('tutor_dashboard'),
        "partner_name": partner_name,
        "partner_initial": partner_name[0].upper() if partner_name else "?",
        "partner_badge": partner_badge,
    }

    return render(request, "core/lesson_room.html", context)


@login_required
@require_POST
def lesson_end(request, match_id: int):
    """レッスン途中退出・タイムアップ時に end_at を今に縮める。
    チューターもオフライン化する（次のポーリングで自動復帰するが意図的退出扱い）。
    """
    match = get_object_or_404(QuickLessonMatch, id=match_id)
    now = timezone.now()

    # end_at をまだ迎えていない場合のみ今に更新（延長はしない）
    if match.end_at is None or match.end_at > now:
        QuickLessonMatch.objects.filter(pk=match.pk).update(end_at=now)

    # チューターをオフライン化
    TutorProfile.objects.filter(pk=match.tutor.pk).update(is_online=False)

    return JsonResponse({"ok": True})


@login_required
def lesson_rating(request, match_id: int):
    match = get_object_or_404(
        QuickLessonMatch.objects.select_related(
            "request__student__user",
            "request__language",
            "tutor__user",
        ),
        id=match_id,
        request__student__user=request.user,
    )

    if request.method == "POST":
        try:
            rating = int(request.POST.get("rating", 0))
        except ValueError:
            rating = 0

        if 1 <= rating <= 5:
            QuickLessonMatch.objects.filter(pk=match.pk).update(
                student_rating=rating,
                student_rated_at=timezone.now(),
            )
            return redirect("create_request")

    return render(request, "core/lesson_rating.html", {"match": match})
