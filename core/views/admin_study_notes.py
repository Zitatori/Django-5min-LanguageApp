"""Read-only administrator access to saved learning materials (never raw private notes)."""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from core.models import StudyNote
from core.services.study_notes import LANGUAGES
from core.views.admin import staff_or_admin_role_required


@login_required
@staff_or_admin_role_required
@never_cache
@require_GET
def admin_study_notes(request, user_id):
    learner = get_object_or_404(User, pk=user_id)
    notes = StudyNote.objects.filter(user=learner, status='ready').defer('content').order_by('-created_at', '-pk')
    return render(request, 'core/admin_study_notes.html', {'learner': learner,
        'notes': Paginator(notes, 20).get_page(request.GET.get('page'))})


@login_required
@staff_or_admin_role_required
@never_cache
@require_GET
def admin_study_note_detail(request, user_id, pk):
    note = get_object_or_404(StudyNote.objects.select_related('user', 'lesson'),
        user_id=user_id, pk=pk, status='ready')
    template = 'core/cheatsheet_detail.html' if note.format == 'cheatsheet' else 'core/study_note_detail.html'
    return render(request, template, {'note': note, 'sheet': note.content,
        'admin_review': True, 'learner': note.user,
        'target_name': _(LANGUAGES.get(note.target_language, note.target_language)),
        'explanation_name': _(LANGUAGES.get(note.explanation_language, note.explanation_language))})
