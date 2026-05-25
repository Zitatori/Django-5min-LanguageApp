from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from core.models import TutorProfile, QuickLessonMatch, LessonLanguage

@staff_member_required
def admin_dashboard(request):
    tutors = TutorProfile.objects.select_related('user').prefetch_related('languages').all()
    matches = QuickLessonMatch.objects.select_related(
        'request__student__user',
        'request__language',
        'tutor__user',
    ).order_by('-started_at')

    languages = LessonLanguage.objects.all()

    return render(request, 'core/admin_dashboard.html', {
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