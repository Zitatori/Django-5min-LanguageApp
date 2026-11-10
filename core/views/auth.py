from django.core import signing
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import redirect, render

from core.forms import SignupForm
from core.models import StudentProfile, TutorProfile, UserProfile
from core.models import PointBalance, PointTransaction

SIGNUP_BONUS_POINTS = 2


def signup(request):
    token = request.GET.get('ref') or request.session.get('referral_token')
    referrer = None
    if token:
        try:
            referrer = User.objects.filter(pk=signing.loads(token, salt='referral-link')).first()
        except (signing.BadSignature, ValueError, TypeError):
            pass
        if referrer:
            request.session['referral_token'] = token

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()

            StudentProfile.objects.get_or_create(user=user)

            referral = referrer.username if referrer else form.cleaned_data.get("referral_source", "").strip()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if referral:
                profile.referral_source = referral
                profile.save()

            wants_to_teach = request.POST.get("wants_to_teach")

            if wants_to_teach:
                TutorProfile.objects.get_or_create(user=user)
                # 言語はサインアップ後に管理者が設定

            # 新規ユーザーにサインアップボーナスを付与
            PointBalance.objects.create(user=user, student_balance=SIGNUP_BONUS_POINTS)
            PointTransaction.objects.create(
                user=user,
                amount=SIGNUP_BONUS_POINTS,
                transaction_type=PointTransaction.TYPE_SIGNUP_BONUS,
                note="Welcome bonus",
            )

            request.session.pop('referral_token', None)
            login(request, user)
            return redirect("home")
    else:
        form = SignupForm(initial={"referral_source": (referrer.first_name or referrer.username) if referrer else ""})

    return render(request, "registration/signup.html", {
        "form": form,
        "signup_bonus": SIGNUP_BONUS_POINTS,
    })
