from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from core.models import LearnerLanguageLevel, LessonLanguage, StudentProfile
from core.templatetags.display_names import level_label


class LearnerLevelForm(forms.Form):
    language = forms.ModelChoiceField(queryset=LessonLanguage.objects.all(), label=_('Study language'))
    level = forms.ChoiceField(label=_('My learning level'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['level'].choices = [('', '—')] + [(x, level_label(x)) for x in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')]


@login_required
@require_http_methods(['GET', 'POST'])
def learner_levels(request):
    current = LearnerLanguageLevel.objects.filter(student__user=request.user, language_id=request.GET.get('language')).first() if str(request.GET.get('language', '')).isdigit() else None
    form = LearnerLevelForm(request.POST if request.method == 'POST' else None,
                            initial={'language': request.GET.get('language'), 'level': current.level if current else ''})
    if request.method == 'POST' and form.is_valid():
        student, _created = StudentProfile.objects.get_or_create(user=request.user)
        LearnerLanguageLevel.objects.update_or_create(student=student, language=form.cleaned_data['language'],
                                                      defaults={'level': form.cleaned_data['level']})
        return redirect('create_request' if request.POST.get('return_to_lessons') == '1' else 'profile')
    return render(request, 'core/learner_levels.html', {'form': form, 'return_to_lessons': request.POST.get('return_to_lessons') == '1'})
