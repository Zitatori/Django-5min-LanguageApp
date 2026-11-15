from unittest.mock import patch
import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import StudyNote, ConversationNote, LessonNoteTranslation
from core.services.note_translation import source_hash
from core.tests import test_study_notes as fixtures
SHEET = fixtures.SHEET


class StudySheetTests(TestCase):
    setUp = fixtures.StudyNoteTests.setUp
    lesson = fixtures.StudyNoteTests.lesson

    def saved(self, **kwargs):
        return StudyNote.objects.create(user=self.user, request_key=uuid.uuid4(), status='ready', content=SHEET,
            target_language='ja', explanation_language='fr', learner_level='A2',
            source_lesson_ids=kwargs.get('ids', [self.match.pk]))

    @patch('core.services.note_translation.request_structured')
    def test_sheet_saved_content_and_translation_without_api(self, api):
        note = self.saved()
        record = ConversationNote.objects.get(match=self.match)
        LessonNoteTranslation.objects.create(note=record, language='fr', status='ready',
            fingerprint=source_hash(record), content={'talked_about': {'translation':'Un commentaire traduit'}, 'advice':{'translation':'Les saisons'}})
        response = self.client.get(reverse('study_note_detail', args=[note.pk]))
        self.assertTemplateUsed(response, 'core/study_sheet.html')
        self.assertContains(response, 'Un commentaire traduit')
        self.assertContains(response, 'Enregistrer en PDF')
        self.assertContains(response, 'celebration-penguin.png')
        self.assertNotContains(response, 'PRIVATE hobbies')
        self.assertNotContains(response, 'sheet.plan')
        api.assert_not_called()
        self.assertTemplateUsed(self.client.get(reverse('study_note_detail', args=[note.pk])+'?view=full'), 'core/study_note_detail.html')

    def test_owner_only_and_foreign_source_ids_ignored(self):
        from core.models import StudentProfile
        other_match = self.lesson(StudentProfile.objects.create(user=self.other))
        ConversationNote.objects.filter(match=other_match).update(talked_about='FOREIGN PRIVATE CONTENT')
        note = self.saved(ids=[self.match.pk, other_match.pk])
        url = reverse('study_note_detail', args=[note.pk])
        self.assertNotContains(self.client.get(url), 'FOREIGN PRIVATE CONTENT')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url+'?view=full').status_code, 404)

    def test_stale_translation_and_old_empty_note(self):
        record = ConversationNote.objects.get(match=self.match)
        LessonNoteTranslation.objects.create(note=record, language='fr', status='ready',
            fingerprint='old', content={'talked_about': {'translation':'STALE TRANSLATION'}})
        note = self.saved()
        response = self.client.get(reverse('study_note_detail', args=[note.pk]))
        self.assertNotContains(response, 'STALE TRANSLATION')
        self.assertContains(response, 'sheet-translate')
        note.content = {}; note.source_lesson_ids = []; note.save()
        self.assertEqual(self.client.get(reverse('study_note_detail', args=[note.pk])).status_code, 200)

    def test_four_explanation_languages_and_escaping(self):
        note = self.saved()
        note.content = dict(SHEET, title='<script>alert(1)</script>')
        for language, label in [('ja','1枚の復習シート'),('en','One-page study sheet'),('fr','Ma fiche de révision'),('es','Mi ficha de repaso')]:
            note.explanation_language = language; note.save()
            response = self.client.get(reverse('study_note_detail', args=[note.pk]))
            self.assertContains(response, label)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '&lt;script&gt;')

    def test_empty_quiz_section_is_hidden_in_both_views(self):
        note = self.saved()
        url = reverse('study_note_detail', args=[note.pk])
        for quiz in ([], None):
            note.content = dict(SHEET, quiz=quiz)
            note.save()
            for suffix in ('', '?view=full'):
                response = self.client.get(url + suffix)
                self.assertNotContains(response, 'Quiz de révision')
                self.assertNotContains(response, 'class="sheet-answers"')
                self.assertNotContains(response, 'class="study-quiz"')
        note.content = dict(SHEET, quiz=[{'question':'Test question', 'options':[{'text':'A'},{'text':'B'},{'text':'C'}], 'correct_index':0, 'explanation':'Test explanation'}])
        note.save()
        for suffix in ('', '?view=full'):
            response = self.client.get(url + suffix)
            self.assertContains(response, 'Quiz de révision')
            self.assertContains(response, 'Test question')
