from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage

@staff_member_required
def admin_dashboard(request):
    users = (
        User.objects
        .select_related('userprofile', 'tutorprofile')
        .prefetch_related('tutorprofile__languages')
        .order_by('date_joined')
    )
    tutors = TutorProfile.objects.select_related('user').prefetch_related('languages').all()
    matches = QuickLessonMatch.objects.select_related(
        'request__student__user',
        'request__language',
        'tutor__user',
    ).order_by('-started_at')

    languages = LessonLanguage.objects.all()

    return render(request, 'core/admin_dashboard.html', {
        'users': users,
        'tutors': tutors,
        'matches': matches,
        'languages': languages,
    })

@staff_member_required
def update_tutor_languages(request, tutor_id):
    if request.method == 'POST':
        tutor = get_object_or_404(TutorProfile, id=tutor_id)
        lang_ids = request.POST.getlist('languages')
        tutor.languages.set(lang_ids)
        return redirect('admin_dashboard')

@staff_member_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:
            user.delete()
    return redirect('admin_dashboard')