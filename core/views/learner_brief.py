from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from core.models import QuickLessonMatch
from core.services.learner_brief import get_or_generate_brief

@login_required
@require_POST
def learner_brief(request, match_id):
    match=get_object_or_404(QuickLessonMatch.objects.select_related('request__language'),
        pk=match_id, tutor__user=request.user)
    return JsonResponse(get_or_generate_brief(match.request.student_id,
        match.request.language_id,match.request.language.name))
