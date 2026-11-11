from core.services.study_display import localized_study_content
from core.services.lesson_lifecycle import completed_lessons
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
from core.models import GoldMembership, StudyNote, QuickLessonMatch
from django.contrib.auth import get_user_model
from core.services.study_notes import LANGUAGES, StudyGenerationError, collect_history, request_study_note


class StudyLessonChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, lesson):
        return '{} · {} · {}'.format(timezone.localtime(lesson.end_at).strftime('%Y-%m-%d %H:%M'), _(lesson.request.language.name), lesson.tutor.user.first_name or lesson.tutor.user.username)


class StudyNoteForm(forms.Form):
    lesson = StudyLessonChoice(queryset=QuickLessonMatch.objects.none(), label=gettext_lazy('Lessons to review'), widget=forms.CheckboxSelectMultiple, required=True)

    def __init__(self, *args, user, gold=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lesson'].required = True
        self.fields['lesson'].queryset = completed_lessons().filter(
            request__student__user=user, request__purpose='lesson',
            student_joined_at__isnull=False, tutor_joined_at__isnull=False,
            end_at__lte=timezone.now(), request__language__code__in=LANGUAGES,
        ).exclude(conversationnote__conversation_not_held=True).select_related('request__language', 'tutor__user').order_by('-end_at', '-pk')

    def clean(self):
        data = super().clean()
        lessons = data.get('lesson')
        if lessons:
            languages = {lesson.request.language.code for lesson in lessons}
            if len(languages) != 1:
                self.add_error('lesson', _('Choose lessons in the same study language.'))
            else:
                data['target_language'] = languages.pop()
        return data

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
    form = StudyNoteForm(request.POST if request.method == 'POST' else None, user=request.user, gold=gold, initial={
        'request_token': new_token(request.user),
        'lesson': [request.GET['lesson']] if request.GET.get('lesson', '').isdigit() else [],
        'explanation_language': getattr(request, 'LANGUAGE_CODE', 'en').split('-')[0],
    })
    error, status = '', 200
    if request.method == 'POST':
        if form.is_valid():
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
                    history, level, ids = collect_history(request.user, data['target_language'], data['include_private_notes'], lesson_ids=[lesson.pk for lesson in data['lesson']])
                    if not history:
                        error = _('No lesson notes are available for this language yet. Complete a lesson and save notes first.')
                    else:
                        # Recover abandoned claims after a worker restart. Normal calls time out within 20 seconds.
                        StudyNote.objects.filter(user=request.user, status='generating', created_at__lt=timezone.now()-timedelta(minutes=5)).update(status='failed', finished_at=timezone.now())
                        try:
                            with transaction.atomic():
                                # Serialize the allowance check across requests/workers for this learner.
                                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                                if not gold:
                                    selected_ids = set(ids)
                                    for saved in StudyNote.objects.filter(user=request.user, format='study_note', status='ready').only('pk', 'source_lesson_ids', 'lesson_id'):
                                        used_ids = set(saved.source_lesson_ids or ([saved.lesson_id] if saved.lesson_id else []))
                                        if selected_ids == used_ids:
                                            return redirect('study_note_detail', pk=saved.pk)
                                        if selected_ids & used_ids:
                                            raise forms.ValidationError(_('Some selected lessons already have study notes. Open the saved notes or select unused lessons.'))
                                note = StudyNote.objects.create(user=request.user, request_key=key,
                                    lesson=data['lesson'][0] if len(data['lesson']) == 1 else None, target_language=data['target_language'], explanation_language=data['explanation_language'],
                                    include_private_notes=data['include_private_notes'], learner_level=level, source_lesson_ids=ids)
                        except forms.ValidationError as exc:
                            error = exc.messages[0]
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
        form = StudyNoteForm(data, user=request.user, gold=gold)
    notes = Paginator(StudyNote.objects.filter(user=request.user, format='study_note', status='ready').defer('content'), 20).get_page(request.GET.get('page'))
    return render(request, 'core/study_notes.html', {'form': form, 'study_gold': gold, 'notes': notes, 'error': error}, status=status)


@login_required
@never_cache
@require_http_methods(['GET'])
def study_note_detail(request, pk):
    # Saved notes remain readable by their owner even if membership later expires.
    note = get_object_or_404(StudyNote, pk=pk, user=request.user, status='ready')
    if note.format == 'cheatsheet':
        return redirect('cheatsheet_detail', pk=note.pk)
    return render(request, 'core/study_note_detail.html', {'note': note, 'sheet': localized_study_content(note.content, note.explanation_language),
        'target_name': _(LANGUAGES[note.target_language]), 'explanation_name': _(LANGUAGES[note.explanation_language])})
