import json
from unittest.mock import patch, MagicMock
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from core.models import ConversationNote, LessonLanguage, QuickLessonRequest, QuickLessonMatch
from core.services.question_generation import generate_for_note, request_questions, QuestionGenerationError
from core.tests.test_conversation_notes import ConversationNotesTests

QUESTIONS = ['What do you like?', 'Where do you go?', 'Who goes with you?', 'When do you go?', 'Why do you like it?']


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
