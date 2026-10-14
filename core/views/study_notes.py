import uuid
from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from core.models import GoldMembership, StudyNote
from core.services.study_notes import LANGUAGES, StudyGenerationError, collect_history, request_study_note


class StudyNoteForm(forms.Form):
    target_language = forms.ChoiceField(label=gettext_lazy('Study language'), choices=[(k, gettext_lazy(v)) for k, v in LANGUAGES.items()])
    explanation_language = forms.ChoiceField(label=gettext_lazy('Explanation language'), choices=[(k, gettext_lazy(v)) for k, v in LANGUAGES.items()])
    include_private_notes = forms.BooleanField(label=gettext_lazy('Include my private notes'), required=False, initial=False)
    request_token = forms.CharField(widget=forms.HiddenInput)


def new_token(user):
    return signing.dumps({'user': user.pk, 'key': str(uuid.uuid4())}, salt='study-notes')


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def study_notes(request):
    gold = GoldMembership.objects.filter(user=request.user, expires_at__gt=timezone.now()).exists()
    form = StudyNoteForm(request.POST if request.method == 'POST' else None, initial={
        'request_token': new_token(request.user),
        'explanation_language': getattr(request, 'LANGUAGE_CODE', 'en').split('-')[0],
        'target_language': 'ja',
    })
    error, status = '', 200
    if request.method == 'POST':
        if not gold:
            error, status = _('Gold membership is required to generate study notes.'), 403
        elif form.is_valid():
            try:
                token = signing.loads(form.cleaned_data['request_token'], salt='study-notes', max_age=86400)
                if token['user'] != request.user.pk:
                    raise ValueError()
                key = uuid.UUID(token['key'])
            except (signing.BadSignature, ValueError, KeyError, TypeError):
                error, status = _('Please reload this page and try again.'), 400
            else:
                previous = StudyNote.objects.filter(user=request.user, request_key=key).first()
                if previous:
                    if previous.status == 'ready':
                        return redirect('study_note_detail', pk=previous.pk)
                    error, status = _('This request was already submitted. Reload to start a new request.'), 409
                else:
                    data = form.cleaned_data
                    history, level, ids = collect_history(request.user, data['target_language'], data['include_private_notes'])
                    if not history:
                        error = _('No lesson notes are available for this language yet. Complete a lesson and save notes first.')
                    else:
                        # Recover abandoned claims after a worker restart. Normal calls time out within 20 seconds.
                        StudyNote.objects.filter(user=request.user, status='generating', created_at__lt=timezone.now()-timedelta(minutes=5)).update(status='failed', finished_at=timezone.now())
                        try:
                            with transaction.atomic():
                                note = StudyNote.objects.create(user=request.user, request_key=key,
                                    target_language=data['target_language'], explanation_language=data['explanation_language'],
                                    include_private_notes=data['include_private_notes'], learner_level=level, source_lesson_ids=ids)
                        except IntegrityError:
                            error, status = _('A study note is already being generated. Please wait, then reload.'), 409
                        else:
                            from django.conf import settings
                            try:
                                content, usage = request_study_note(data['target_language'], data['explanation_language'], level, history)
                            except StudyGenerationError:
                                StudyNote.objects.filter(pk=note.pk, status='generating').update(status='failed', finished_at=timezone.now())
                                error = _('Study notes could not be generated. Please try again later. Your lesson notes are safe.')
                            else:
                                StudyNote.objects.filter(pk=note.pk, status='generating').update(content=content, status='ready',
                                    model=settings.OPENAI_STUDY_MODEL, finished_at=timezone.now(), **usage)
                                return redirect('study_note_detail', pk=note.pk)
        else:
            status = 400
    # A failed response receives a fresh key; an old/replayed POST still cannot call the API twice.
    if request.method == 'POST':
        data = request.POST.copy()
        data['request_token'] = new_token(request.user)
        form = StudyNoteForm(data)
    notes = Paginator(StudyNote.objects.filter(user=request.user, status='ready').defer('content'), 20).get_page(request.GET.get('page'))
    return render(request, 'core/study_notes.html', {'form': form, 'study_gold': gold, 'notes': notes, 'error': error}, status=status)


@login_required
@never_cache
@require_http_methods(['GET'])
def study_note_detail(request, pk):
    # Saved notes remain readable by their owner even if membership later expires.
    note = get_object_or_404(StudyNote, pk=pk, user=request.user, status='ready')
    return render(request, 'core/study_note_detail.html', {'note': note, 'sheet': note.content,
        'target_name': _(LANGUAGES[note.target_language]), 'explanation_name': _(LANGUAGES[note.explanation_language])})
