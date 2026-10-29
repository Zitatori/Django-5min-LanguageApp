from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ConversationNote, LessonLanguage, QuickLessonMatch, QuickLessonRequest, StudentProfile, TutorProfile


@override_settings(OPENAI_API_KEY="")
class ConversationNotesTests(TestCase):
    def setUp(self):
        self.tutor = TutorProfile.objects.create(user=User.objects.create_user(username='note-tutor'))
        student = StudentProfile.objects.create(user=User.objects.create_user(username='note-student'))
        language = LessonLanguage.objects.create(code='en', name='English')
        request = QuickLessonRequest.objects.create(student=student, language=language, status='matched')
        self.match = QuickLessonMatch.objects.create(request=request, tutor=self.tutor)
        self.client.force_login(self.tutor.user)
        self.url = reverse('lesson_note', args=[self.match.pk])

    def test_form_requests_level_and_conversation_content(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="talked_about"')
        self.assertContains(response, 'name="learner_level"')
        self.assertContains(response, 'name="next_conversation"')
        self.assertContains(response, 'name="conversation_not_held"')

    def test_save_level_and_both_notes(self):
        self.client.post(self.url, {'talked_about': '  Discussed hiking.  ', 'learner_level': 'A2', 'next_conversation': 'Old field'})
        note = ConversationNote.objects.get(match=self.match)
        self.assertEqual(note.talked_about, 'Discussed hiking.')
        self.assertEqual(note.note, 'Discussed hiking.')
        self.assertEqual(note.learner_level, 'A2')
        self.assertEqual(note.next_conversation, 'Old field')

    def test_blank_content_does_not_create_note(self):
        self.client.post(self.url, {'talked_about': '   '})
        self.assertFalse(ConversationNote.objects.exists())

    def test_legacy_notes_keep_content_without_structured_summary(self):
        self.assertEqual(ConversationNote(note='Legacy text').conversation_content, 'Legacy text')
        self.assertEqual(ConversationNote(note='Combined summary', talked_about='Travel', learner_level='B1', next_conversation='Next question').conversation_content, 'Travel')
        self.assertEqual(ConversationNote(note='Level-only summary', learner_level='A1').conversation_content, '')

    def test_level_can_be_saved_without_conversation_content(self):
        self.client.post(self.url, {'learner_level': 'B1', 'conversation_not_held': 'on'})
        note = ConversationNote.objects.get(match=self.match)
        self.assertEqual(note.learner_level, 'B1')
        self.assertEqual(note.match.request.language.code, 'en')

    def test_invalid_level_is_not_saved(self):
        self.client.post(self.url, {'learner_level': 'invalid', 'talked_about': 'Travel', 'next_conversation': 'Past tense'})
        self.assertEqual(ConversationNote.objects.get(match=self.match).learner_level, '')

    def test_both_fields_required_and_input_preserved(self):
        for data in ({'talked_about': 'Travel', 'learner_level': 'A2'},
                     {'next_conversation': 'Past tense'},
                     {'talked_about': '  ', 'next_conversation': '  '}):
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertFalse(ConversationNote.objects.exists())
            for field, value in data.items():
                self.assertEqual(response.context['form'][field].value(), value)

    def test_not_held_can_save_empty_without_generating(self):
        from unittest.mock import patch
        with patch('core.views.lesson.generate_for_note') as generate:
            response = self.client.post(self.url, {'conversation_not_held': 'on'})
        self.assertEqual(response.status_code, 302)
        note = ConversationNote.objects.get(match=self.match)
        self.assertTrue(note.conversation_not_held)
        self.assertEqual(note.talked_about, '')
        self.assertEqual(note.next_conversation, '')
        generate.assert_not_called()

    def test_oversized_note_rejected_without_truncation(self):
        response = self.client.post(self.url, {'talked_about': 'a' * 501, 'next_conversation': 'Practice'})
        self.assertIn('talked_about', response.context['form'].errors)
        self.assertFalse(ConversationNote.objects.exists())

    def test_other_tutor_cannot_save(self):
        other = User.objects.create_user(username='other-tutor')
        self.client.force_login(other)
        response = self.client.post(self.url, {'conversation_not_held': 'on'})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ConversationNote.objects.exists())

    def test_duplicate_save_does_not_create_another_note(self):
        data = {'talked_about': 'Travel', 'next_conversation': 'Past tense'}
        self.client.post(self.url, data)
        self.client.post(self.url, data)
        self.assertEqual(ConversationNote.objects.filter(match=self.match).count(), 1)

    def test_translated_labels(self):
        from django.utils.translation import override
        for language, label in [('ja', '勉強した方がいいこと'), ('en', 'What to study'),
                                ('fr', 'À étudier'), ('es', 'Qué estudiar')]:
            self.client.cookies['django_language'] = language
            self.assertContains(self.client.get(self.url), label)
