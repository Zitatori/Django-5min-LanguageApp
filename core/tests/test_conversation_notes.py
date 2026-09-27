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
        self.assertNotContains(response, 'name="next_conversation"')

    def test_save_level_and_content_and_ignore_removed_field(self):
        self.client.post(self.url, {'talked_about': '  Discussed hiking.  ', 'learner_level': 'A2', 'next_conversation': 'Old field'})
        note = ConversationNote.objects.get(match=self.match)
        self.assertEqual(note.talked_about, 'Discussed hiking.')
        self.assertEqual(note.note, 'Discussed hiking.')
        self.assertEqual(note.learner_level, 'A2')
        self.assertEqual(note.next_conversation, '')

    def test_blank_content_does_not_create_note(self):
        self.client.post(self.url, {'talked_about': '   '})
        self.assertFalse(ConversationNote.objects.exists())

    def test_legacy_notes_keep_content_without_structured_summary(self):
        self.assertEqual(ConversationNote(note='Legacy text').conversation_content, 'Legacy text')
        self.assertEqual(ConversationNote(note='Combined summary', talked_about='Travel', learner_level='B1', next_conversation='Next question').conversation_content, 'Travel')
        self.assertEqual(ConversationNote(note='Level-only summary', learner_level='A1').conversation_content, '')

    def test_level_can_be_saved_without_conversation_content(self):
        self.client.post(self.url, {'learner_level': 'B1'})
        note = ConversationNote.objects.get(match=self.match)
        self.assertEqual(note.learner_level, 'B1')
        self.assertEqual(note.match.request.language.code, 'en')

    def test_invalid_level_is_not_saved(self):
        self.client.post(self.url, {'learner_level': 'invalid', 'talked_about': 'Travel'})
        self.assertEqual(ConversationNote.objects.get(match=self.match).learner_level, '')
