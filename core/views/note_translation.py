from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from core.models import ConversationNote
from core.services.note_translation import translate_notes
from core.services.study_notes import LANGUAGES, StudyGenerationError

@login_required
@never_cache
@require_POST
def note_translation(request, note_id):
    note = get_object_or_404(ConversationNote, pk=note_id, student__user=request.user)
    language = request.POST.get('language', getattr(request, 'LANGUAGE_CODE','en').split('-')[0])
    if language not in LANGUAGES:
        return render(request, 'core/_note_translation.html', {'translation_error':_('Choose a supported explanation language.')}, status=400)
    try:
        content = translate_notes([note],language)[note.pk]
    except StudyGenerationError:
        return render(request, 'core/_note_translation.html', {'translation_error':_('Translation is temporarily unavailable. Your original notes are safe. Please try again.')}, status=503)
    return render(request, 'core/_note_translation.html', {'record_translation':content})
