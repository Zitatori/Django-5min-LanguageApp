from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from core.models import StudentProfile, TutorProfile, LessonLanguage
from core.models import PointBalance, PointTransaction

SIGNUP_BONUS_POINTS = 10


def signup(request):
    languages = LessonLanguage.objects.all()

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            StudentProfile.objects.get_or_create(user=user)

            wants_to_teach = request.POST.get("wants_to_teach")
            selected_languages = request.POST.getlist("tutor_languages")

            if wants_to_teach:
                tutor_profile, _ = TutorProfile.objects.get_or_create(user=user)
                tutor_profile.languages.set(selected_languages)
                tutor_profile.save()

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
        "languages": languages,
    })