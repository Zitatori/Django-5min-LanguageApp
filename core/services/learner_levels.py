from core.models import LearnerLanguageLevel


def self_level(user, language_code):
    return LearnerLanguageLevel.objects.filter(student__user=user, language__code=language_code).values_list('level', flat=True).first() or ''
