from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from core.models import StudentProfile, LessonLanguage, LearnerLanguageLevel, QuickLessonRequest
from core.services.study_notes import collect_history
from core.services.learner_levels import self_level


class LearnerLevelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('self-level')
        self.student = StudentProfile.objects.create(user=self.user)
        self.ja = LessonLanguage.objects.create(code='ja', name='Japanese')
        self.fr = LessonLanguage.objects.create(code='fr', name='French')
        self.client.force_login(self.user)

    def test_save_change_and_separate_languages(self):
        for lang, level in [(self.ja, 'A1'), (self.fr, 'B2'), (self.ja, 'A2')]:
            self.assertEqual(self.client.post(reverse('learner_levels'), {'language': lang.pk, 'level': level}).status_code, 302)
        self.assertEqual(self_level(self.user, 'ja'), 'A2')
        self.assertEqual(self_level(self.user, 'fr'), 'B2')
        self.assertEqual(LearnerLanguageLevel.objects.count(), 2)
        self.assertEqual(collect_history(self.user, 'ja', False)[1], 'A2')

    def test_invalid_and_other_user_are_isolated(self):
        self.client.post(reverse('learner_levels'), {'language': self.ja.pk, 'level': 'C9'})
        self.assertFalse(LearnerLanguageLevel.objects.exists())
        other = User.objects.create_user('other-level')
        self.client.post(reverse('learner_levels'), {'language': self.ja.pk, 'level': 'A1', 'user': other.pk})
        self.assertEqual(self_level(other, 'ja'), '')

    def test_first_lesson_requires_selection_before_matching(self):
        response = self.client.post(reverse('create_request'), {'language_id': self.ja.pk})
        self.assertTemplateUsed(response, 'core/learner_levels.html')
        self.assertFalse(QuickLessonRequest.objects.exists())
        LearnerLanguageLevel.objects.create(student=self.student, language=self.ja, level='A1')
        response = self.client.post(reverse('create_request'), {'language_id': self.ja.pk})
        self.assertEqual(response.status_code, 302)

    def test_existing_setting_is_preselected(self):
        LearnerLanguageLevel.objects.create(student=self.student, language=self.ja, level='B1')
        response = self.client.get(reverse('learner_levels'), {'language': self.ja.pk})
        self.assertEqual(response.context['form'].initial['level'], 'B1')
