import json
from unittest.mock import patch, MagicMock
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from core.models import ConversationNote, LessonLanguage, QuickLessonRequest, QuickLessonMatch
from core.services.question_generation import generate_for_note, request_questions, QuestionGenerationError
from core.tests.test_conversation_notes import ConversationNotesTests

QUESTIONS = ['What do you like?', 'Where do you go?', 'Who goes with you?', 'When do you go?', 'Why do you like it?']


@override_settings(OPENAI_API_KEY='test-only-key')
class QuestionGenerationTests(ConversationNotesTests):
    def test_history_is_scoped_to_language_and_latest_level_is_used(self):
        student = self.match.request.student
        other = LessonLanguage.objects.create(code='fr', name='French')
        other_match = QuickLessonMatch.objects.create(request=QuickLessonRequest.objects.create(student=student, language=other), tutor=self.tutor)
        ConversationNote.objects.create(student=student, tutor=self.tutor, match=other_match, talked_about='French-only topic', learner_level='C2')
        ConversationNote.objects.create(student=student, tutor=self.tutor, match=self.match, talked_about='Earlier English topic', learner_level='A2')
        note = ConversationNote.objects.create(student=student, tutor=self.tutor, match=self.match, talked_about='Hiking')
        with patch('core.services.question_generation.request_questions', return_value=QUESTIONS) as api:
            generate_for_note(note)
            generate_for_note(note)
        api.assert_called_once_with('English', 'A2', ['Earlier English topic', 'Hiking'], previous_questions=[])
        note.refresh_from_db()
        self.assertEqual(note.suggested_questions, QUESTIONS)
        self.assertEqual(note.questions_level, 'A2')

    def test_repeated_post_saves_and_generates_once(self):
        with patch('core.services.question_generation.request_questions', return_value=QUESTIONS) as api:
            for _ in range(2):
                response = self.client.post(self.url, {'talked_about': 'Hiking', 'learner_level': 'A1', 'next_conversation': 'Practice past tense'})
                self.assertEqual(response.status_code, 302)
        self.assertEqual(ConversationNote.objects.filter(match=self.match).count(), 1)
        api.assert_called_once()

    def test_api_failure_preserves_note(self):
        with patch('core.services.question_generation.request_questions', side_effect=QuestionGenerationError):
            response = self.client.post(self.url, {'talked_about': 'Hiking', 'learner_level': 'A1', 'next_conversation': 'Practice past tense'})
        self.assertEqual(response.status_code, 302)
        note = ConversationNote.objects.get(match=self.match)
        self.assertEqual(note.talked_about, 'Hiking')
        self.assertEqual(note.questions_status, 'unavailable')

    def test_tutor_room_renders_stored_questions_without_api_call(self):
        ConversationNote.objects.create(student=self.match.request.student, tutor=self.tutor, match=self.match,
            talked_about='Hiking', suggested_questions=QUESTIONS, questions_level='A2', questions_status='ready')
        with patch('core.services.question_generation.request_questions') as api:
            response = self.client.get(reverse('lesson_room', args=[self.match.pk]))
        self.assertContains(response, QUESTIONS[0])
        api.assert_not_called()

    def test_save_both_notes_with_generation(self):
        with patch('core.services.question_generation.request_questions', return_value=QUESTIONS):
            super().test_save_level_and_both_notes()

    # Inherited tests also remain offline.
    def setUp(self):
        super().setUp()
        mock = patch('core.services.question_generation.request_questions', return_value=QUESTIONS)
        mock.start()
        self.addCleanup(mock.stop)


@override_settings(OPENAI_API_KEY='test-only-key', OPENAI_QUESTION_MODEL='gpt-4.1-mini')
class ResponseValidationTests(SimpleTestCase):
    @patch('core.services.question_generation.urlopen')
    def test_structured_response_and_private_request(self, transport):
        response = MagicMock()
        response.read.return_value = json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'follow_up_questions': QUESTIONS[:3], 'new_topic_questions': QUESTIONS[3:]})}]}]}).encode()
        transport.return_value.__enter__.return_value = response
        self.assertEqual(request_questions('English', 'A1', ['Hiking']), QUESTIONS)
        payload = json.loads(transport.call_args.args[0].data)
        self.assertFalse(payload['store'])
        self.assertEqual(json.loads(payload['input'])['cefr_level'], 'A1')

    @patch('core.services.question_generation.urlopen')
    def test_refusal_does_not_save_questions(self, transport):
        response = MagicMock()
        response.read.return_value = json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]}).encode()
        transport.return_value.__enter__.return_value = response
        with self.assertRaises(QuestionGenerationError):
            request_questions('English', 'A1', [])


    @patch('core.services.question_generation.urlopen')
    def test_question_mix_and_previous_questions_are_sent(self, transport):
        response = MagicMock()
        response.read.return_value = json.dumps({'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({
                'follow_up_questions': QUESTIONS[:3], 'new_topic_questions': QUESTIONS[3:]})}]}]}).encode()
        transport.return_value.__enter__.return_value = response
        self.assertEqual(request_questions('Japanese', 'A1', ['Older lesson', 'Latest lesson'], ['Earlier question?']), QUESTIONS)
        payload = json.loads(transport.call_args.args[0].data)
        context = json.loads(payload['input'])
        self.assertEqual(context['latest_lesson'], 'Latest lesson')
        self.assertEqual(context['previous_questions'], ['Earlier question?'])
        properties = payload['text']['format']['schema']['properties']
        self.assertEqual(properties['follow_up_questions']['maxItems'], 3)
        self.assertEqual(properties['new_topic_questions']['maxItems'], 2)

    @patch('core.services.question_generation.urlopen')
    def test_wrong_mix_duplicates_and_previous_repeats_are_rejected(self, transport):
        cases = [
            ({'follow_up_questions': QUESTIONS[:4], 'new_topic_questions': QUESTIONS[4:]}, []),
            ({'follow_up_questions': QUESTIONS[:3], 'new_topic_questions': [QUESTIONS[0], QUESTIONS[4]]}, []),
            ({'follow_up_questions': QUESTIONS[:3], 'new_topic_questions': QUESTIONS[3:]}, [QUESTIONS[0].upper()]),
        ]
        for groups, previous in cases:
            response = MagicMock()
            response.read.return_value = json.dumps({'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(groups)}]}]}).encode()
            transport.return_value.__enter__.return_value = response
            with self.assertRaises(QuestionGenerationError):
                request_questions('English', 'A2', ['Food'], previous)
