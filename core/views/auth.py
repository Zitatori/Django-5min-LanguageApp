from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from core.models import StudentProfile, TutorProfile
from core.models import PointBalance, PointTransaction

SIGNUP_BONUS_POINTS = 10


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            StudentProfile.objects.get_or_create(user=user)

            wants_to_teach = request.POST.get("wants_to_teach")

            if wants_to_teach:
                TutorProfile.objects.get_or_create(user=user)
                # 言語はサインアップ後に管理者が設定

            # 新規ユーザーにサインアップボーナスを付与
            PointBalance.objects.create(user=user, balance=SIGNUP_BONUS_POINTS)
            PointTransaction.objects.create(
                user=user,
                amount=SIGNUP_BONUS_POINTS,
                transaction_type=PointTransaction.TYPE_SIGNUP_BONUS,
                note="Welcome bonus",
            )

            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {
        "form": form,
    })