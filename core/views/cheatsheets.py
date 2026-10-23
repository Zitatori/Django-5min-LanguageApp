"""Owner-only lesson cheatsheets; existing Gold and generation lock are reused."""
import uuid
from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from core.models import GoldMembership, QuickLessonMatch, StudyNote
from core.services.cheatsheets import collect_context, generate_cheatsheet
from core.services.study_notes import LANGUAGES, StudyGenerationError
from core.views.study_notes import new_token


def eligible_lessons(user):
    return QuickLessonMatch.objects.filter(request__student__user=user,
        request__language__code='ja', request__purpose='lesson',
        student_joined_at__isnull=False, tutor_joined_at__isnull=False,
        end_at__lte=timezone.now()).select_related('request', 'tutor__user').order_by('-end_at', '-pk')


class LessonChoice(forms.ModelChoiceField):
    def label_from_instance(self, lesson):
        return '#{} · {}'.format(lesson.pk, timezone.localtime(lesson.end_at).strftime('%Y-%m-%d %H:%M'))


class CheatsheetForm(forms.Form):
    lesson = LessonChoice(queryset=QuickLessonMatch.objects.none(), label=gettext_lazy('Lesson'))
    explanation_language = forms.ChoiceField(label=gettext_lazy('Explanation language'),
        choices=[(key, gettext_lazy(name)) for key, name in LANGUAGES.items()])
    request_token = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lesson'].queryset = eligible_lessons(user)


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def cheatsheets(request):
    gold = GoldMembership.objects.filter(user=request.user, expires_at__gt=timezone.now()).exists()
    initial = {'request_token': new_token(request.user), 'lesson': request.GET.get('lesson'),
               'explanation_language': getattr(request, 'LANGUAGE_CODE', 'en').split('-')[0]}
    form = CheatsheetForm(request.POST or None, user=request.user, initial=initial)
    error, status = '', 200
    if request.method == 'POST':
        if not gold:
            error, status = _('Gold membership is required to generate study notes.'), 403
        elif not form.is_valid():
            status = 400
        else:
            try:
                token = signing.loads(form.cleaned_data['request_token'], salt='study-notes', max_age=86400)
                if token['user'] != request.user.pk:
                    raise ValueError()
                key = uuid.UUID(token['key'])
            except (signing.BadSignature, KeyError, ValueError, TypeError):
                error, status = _('Please reload this page and try again.'), 400
            else:
                lesson = form.cleaned_data['lesson']
                existing = StudyNote.objects.filter(user=request.user, format='cheatsheet', lesson=lesson,
                                                   status='ready').first()
                if existing:
                    return redirect('cheatsheet_detail', pk=existing.pk)
                if StudyNote.objects.filter(user=request.user, request_key=key).exists():
                    error, status = _('This request was already submitted. Reload to start a new request.'), 409
                else:
                    context = collect_context(request.user, lesson)
                    if not context:
                        error = _('Your tutor needs to record lesson content and a level before a cheatsheet can be generated.')
                    else:
                        StudyNote.objects.filter(user=request.user, status='generating',
                            created_at__lt=timezone.now()-timedelta(minutes=5)).update(status='failed', finished_at=timezone.now())
                        try:
                            with transaction.atomic():
                                sheet = StudyNote.objects.create(user=request.user, request_key=key,
                                    format='cheatsheet', lesson=lesson, target_language='ja',
                                    explanation_language=form.cleaned_data['explanation_language'],
                                    learner_level=context['level'], source_lesson_ids=[lesson.pk])
                        except IntegrityError:
                            error, status = _('A study note is already being generated. Please wait, then reload.'), 409
                        else:
                            try:
                                content, usage = generate_cheatsheet(sheet.explanation_language, context)
                            except StudyGenerationError:
                                StudyNote.objects.filter(pk=sheet.pk, status='generating').update(status='failed', finished_at=timezone.now())
                                error = _('We could not create a verified cheatsheet. Please try again later. Your notes are safe.')
                            else:
                                updated = StudyNote.objects.filter(pk=sheet.pk, status='generating').update(content=content,
                                    status='ready', model=settings.OPENAI_STUDY_MODEL, finished_at=timezone.now(), **usage)
                                if updated:
                                    return redirect('cheatsheet_detail', pk=sheet.pk)
                                error = _('Please reload this page and try again.')
    if request.method == 'POST':
        data = request.POST.copy(); data['request_token'] = new_token(request.user)
        form = CheatsheetForm(data, user=request.user)
    saved = StudyNote.objects.filter(user=request.user, format='cheatsheet', status='ready').select_related('lesson')
    return render(request, 'core/cheatsheets.html', {'form': form, 'study_gold': gold,
        'error': error, 'latest': saved.first(), 'notes': Paginator(saved, 12).get_page(request.GET.get('page'))}, status=status)


@login_required
@never_cache
@require_http_methods(['GET'])
def cheatsheet_detail(request, pk):
    note = get_object_or_404(StudyNote.objects.select_related('lesson'), pk=pk,
        user=request.user, format='cheatsheet', status='ready')
    own = StudyNote.objects.filter(user=request.user, format='cheatsheet', status='ready')
    previous = own.filter(Q(created_at__lt=note.created_at) | Q(created_at=note.created_at, pk__lt=note.pk)).order_by('-created_at', '-pk').first()
    following = own.filter(Q(created_at__gt=note.created_at) | Q(created_at=note.created_at, pk__gt=note.pk)).order_by('created_at', 'pk').first()
    return render(request, 'core/cheatsheet_detail.html', {'note': note, 'sheet': note.content,
        'previous': previous, 'following': following})
