import copy
import json
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import ConversationNote, GoldMembership, LessonLanguage, QuickLessonMatch, QuickLessonRequest, StudentProfile, StudyNote, TutorProfile
from core.services.study_notes import collect_history, request_study_note, StudyGenerationError, study_schema, validate, validate_readings
from core.views.study_notes import new_token

SHEET = {'quiz': [], 'title': 'Weather review', 'priorities': ['Weather', 'Seasons', 'Likes'],
         'vocabulary': [{'term': '天気', 'reading': 'てんき', 'pronunciation': 'tenki', 'meaning': 'météo', 'example': 'いい天気です。', 'example_translation': 'Il fait beau.'}],
         'grammar': [], 'corrections': [], 'conversation': [{'question': '冬が好きですか？', 'answer': 'はい、好きです。', 'question_translation': 'Aimez-vous l’hiver ?', 'answer_translation': 'Oui, j’aime cela.'}],
         'plan': [{'minutes': 5, 'activity': 'Read'}, {'minutes': 5, 'activity': 'Practice'}], 'next_topics': ['Seasons']}
USAGE = {'input_tokens': 300, 'output_tokens': 500}


@override_settings(LANGUAGE_CODE='en')
class StudyNoteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('learner-id', email='private@example.com', first_name='Maria')
        self.other = User.objects.create_user('other-learner')
        self.student = StudentProfile.objects.create(user=self.user)
        self.tutor = TutorProfile.objects.create(user=User.objects.create_user('teacher-id'))
        self.language = LessonLanguage.objects.create(code='ja', name='Japanese')
        self.gold = GoldMembership.objects.create(user=self.user, expires_at=timezone.now()+timedelta(days=30))
        self.match = self.lesson(self.student)
        self.client.force_login(self.user)
        self.url = reverse('study_notes')

    def lesson(self, student, language=None):
        req = QuickLessonRequest.objects.create(student=student, language=language or self.language)
        match = QuickLessonMatch.objects.create(request=req, tutor=self.tutor, student_joined_at=timezone.now(),
            tutor_joined_at=timezone.now(), started_at=timezone.now()-timedelta(minutes=6), end_at=timezone.now()-timedelta(seconds=1), student_private_note='PRIVATE hobbies')
        ConversationNote.objects.create(student=student, tutor=self.tutor, match=match, learner_level='A2',
            talked_about='Weather. Maria private@example.com', next_conversation='Discuss seasons')
        return match

    def data(self, **changes):
        data = {'lesson': [self.match.pk], 'request_token': new_token(self.user), 'target_language': 'ja', 'explanation_language': 'fr'}
        data.update(changes)
        return data

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_gold_generate_save_replay_and_read_without_api(self, api):
        data = self.data()
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        note = StudyNote.objects.get()
        self.assertEqual(note.status, 'ready')
        self.assertEqual(note.explanation_language, 'fr')
        self.assertFalse(note.include_private_notes)
        self.assertEqual(note.input_tokens, 300)
        self.assertNotIn('private_notes', api.call_args.args[3][0])
        self.assertNotIn('Maria', json.dumps(api.call_args.args[3]))
        self.assertNotIn('private@example.com', json.dumps(api.call_args.args[3]))
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertContains(self.client.get(response.url), 'Weather review')
        self.assertContains(self.client.get(self.url), str(note.pk))
        self.assertEqual(api.call_count, 1)

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_private_opt_in_and_unlimited_sequential_generation(self, api):
        for _ in range(8):
            self.assertEqual(self.client.post(self.url, self.data(include_private_notes='on')).status_code, 302)
        self.assertEqual(api.call_count, 8)
        self.assertEqual(StudyNote.objects.filter(status='ready').count(), 8)
        self.assertEqual(api.call_args.args[3][0]['private_notes'], 'PRIVATE hobbies')

    @patch('core.views.study_notes.request_study_note')
    def test_non_gold_requires_a_lesson_even_for_staff(self, api):
        self.gold.expires_at = timezone.now()-timedelta(days=1)
        self.gold.save()
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.post(self.url, self.data(lesson=[])).status_code, 400)
        self.gold.delete()
        self.assertEqual(self.client.post(self.url, self.data(lesson=[])).status_code, 400)
        self.assertContains(self.client.get(self.url), 'id="study-form"')
        api.assert_not_called()

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_free_user_once_per_lesson_and_private_choice(self, api):
        self.gold.delete()
        data = self.data(lesson=self.match.pk, target_language='es')
        first = self.client.post(self.url, data)
        self.assertEqual(first.status_code, 302)
        note = StudyNote.objects.get()
        self.assertEqual(note.lesson_id, self.match.pk)
        self.assertEqual(note.target_language, 'ja')
        self.assertEqual(note.source_lesson_ids, [self.match.pk])
        self.assertNotIn('private_notes', api.call_args.args[3][0])
        again = self.client.post(self.url, self.data(lesson=self.match.pk, explanation_language='en'))
        self.assertEqual(again.url, first.url)
        self.assertEqual(api.call_count, 1)
        second = self.lesson(self.student)
        self.assertEqual(self.client.post(self.url, self.data(lesson=second.pk, include_private_notes='on')).status_code, 302)
        self.assertEqual(api.call_count, 2)
        self.assertIn('private_notes', api.call_args.args[3][0])
        self.assertEqual(self.client.get(first.url).status_code, 200)
        self.assertEqual(api.call_count, 2)

    @patch('core.views.study_notes.request_study_note', side_effect=[StudyGenerationError(), (SHEET, USAGE)])
    def test_free_failure_does_not_use_allowance(self, api):
        self.gold.delete()
        self.assertEqual(self.client.post(self.url, self.data(lesson=self.match.pk)).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.data(lesson=self.match.pk)).status_code, 302)
        self.assertEqual(api.call_count, 2)

    @patch('core.views.study_notes.request_study_note')
    def test_free_cannot_select_someone_elses_lesson(self, api):
        self.gold.delete()
        other = self.lesson(StudentProfile.objects.create(user=self.other))
        self.assertEqual(self.client.post(self.url, self.data(lesson=other.pk)).status_code, 400)
        api.assert_not_called()

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_gold_can_repeat_selected_lesson(self, api):
        for _ in range(2):
            self.assertEqual(self.client.post(self.url, self.data(lesson=self.match.pk)).status_code, 302)
        self.assertEqual(api.call_count, 2)

    @patch('core.views.study_notes.request_study_note')
    def test_no_history_and_wrong_language_do_not_call_api(self, api):
        self.assertEqual(self.client.post(self.url, self.data(lesson=[])).status_code, 400)
        api.assert_not_called()

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_multiple_selection_includes_all_and_preserves_free_allowance(self, api):
        self.gold.delete()
        selected = [self.match] + [self.lesson(self.student) for _ in range(5)]
        ids = [m.pk for m in selected]
        response = self.client.post(self.url, self.data(lesson=ids))
        self.assertEqual(response.status_code, 302)
        note = StudyNote.objects.get(status='ready')
        self.assertEqual(set(note.source_lesson_ids), set(ids))
        self.assertIsNone(note.lesson_id)
        self.assertEqual(len(api.call_args.args[3]), 6)
        self.assertTrue(all('private_notes' not in row for row in api.call_args.args[3]))
        self.assertEqual(self.client.post(self.url, self.data(lesson=list(reversed(ids)))).url, response.url)
        new_lesson = self.lesson(self.student)
        blocked = self.client.post(self.url, self.data(lesson=[ids[0], new_lesson.pk]))
        self.assertContains(blocked, 'already have study notes')
        self.assertEqual(api.call_count, 1)

    @patch('core.views.study_notes.request_study_note')
    def test_mixed_language_and_foreign_selection_rejected(self, api):
        english = LessonLanguage.objects.create(code='en', name='English')
        other_language = self.lesson(self.student, english)
        foreign = self.lesson(StudentProfile.objects.create(user=self.other))
        for lesson in [other_language, foreign]:
            self.assertEqual(self.client.post(self.url, self.data(lesson=[self.match.pk, lesson.pk])).status_code, 400)
        api.assert_not_called()

    def test_picker_has_no_target_language_or_technical_lesson_number(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'type="checkbox" name="lesson"')
        self.assertNotContains(response, 'name="target_language"')
        self.assertNotContains(response, ' · #')

    def test_only_own_latest_five_completed_matching_lessons(self):
        old_id = self.match.pk
        for _ in range(6): self.lesson(self.student)
        other_student = StudentProfile.objects.create(user=self.other)
        other_match = self.lesson(other_student)
        english = LessonLanguage.objects.create(code='en', name='English')
        english_match = self.lesson(self.student, english)
        future = self.lesson(self.student)
        future.end_at = timezone.now()+timedelta(hours=1)
        future.save()
        history, level, ids = collect_history(self.user, 'ja', False)
        self.assertEqual(len(ids), 5)
        self.assertEqual(level, 'A2')
        for pk in [old_id, other_match.pk, english_match.pk, future.pk]: self.assertNotIn(pk, ids)

    @patch('core.views.study_notes.request_study_note', side_effect=StudyGenerationError)
    def test_api_failure_releases_claim_and_replay_does_not_retry(self, api):
        data = self.data()
        self.assertContains(self.client.post(self.url, data), 'could not be generated')
        self.assertEqual(StudyNote.objects.get().status, 'failed')
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(self.match.student_private_note, 'PRIVATE hobbies')

    @patch('core.views.study_notes.request_study_note')
    def test_concurrent_claim_rejected_and_db_enforces_it(self, api):
        StudyNote.objects.create(user=self.user, request_key=uuid.uuid4(), target_language='ja', explanation_language='fr')
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 409)
        api.assert_not_called()
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudyNote.objects.create(user=self.user, request_key=uuid.uuid4(), target_language='en', explanation_language='en')

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_stale_claim_recovery(self, api):
        note = StudyNote.objects.create(user=self.user, request_key=uuid.uuid4(), target_language='ja', explanation_language='fr')
        StudyNote.objects.filter(pk=note.pk).update(created_at=timezone.now()-timedelta(minutes=6))
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.status, 'failed')

    @patch('core.views.study_notes.request_study_note', return_value=(SHEET, USAGE))
    def test_other_user_cannot_read_notes(self, api):
        response = self.client.post(self.url, self.data(include_private_notes='on'))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(response.url).status_code, 404)
        self.assertNotContains(self.client.get(self.url), 'Weather review')
        self.client.force_login(self.tutor.user)
        self.assertEqual(self.client.get(response.url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(response.url).status_code, 302)

    @patch('core.views.study_notes.request_study_note')
    def test_invalid_languages_token_and_foreign_token(self, api):
        for data in [self.data(explanation_language='xx'), self.data(request_token='invalid'), self.data(request_token=new_token(self.other))]:
            self.assertEqual(self.client.post(self.url, data).status_code, 400)
        api.assert_not_called()

    def test_four_locales_and_opt_in_off_by_default(self):
        for lang, title in [('ja','AI復習ノート'), ('en','AI Study Notes'), ('fr','Fiches de révision IA'), ('es','Notas de repaso con IA')]:
            response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE=lang)
            self.assertContains(response, title)
            self.assertFalse(response.context['form']['include_private_notes'].value())

    @patch('core.views.study_notes.request_study_note')
    def test_generated_html_is_escaped(self, api):
        sheet = copy.deepcopy(SHEET)
        sheet['title'] = '<script>alert(1)</script>'
        api.return_value = sheet, USAGE
        response = self.client.post(self.url, self.data())
        detail = self.client.get(response.url)
        self.assertContains(detail, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(detail, '<script>alert(1)</script>')


@override_settings(OPENAI_API_KEY='test-placeholder', OPENAI_STUDY_MODEL='gpt-4.1-mini', OPENAI_STUDY_TIMEOUT_SECONDS=20, OPENAI_STUDY_MAX_OUTPUT_TOKENS=3600)
class StudyAPITests(TestCase):
    def response(self, sheet=None, **overrides):
        sheet = copy.deepcopy(sheet or SHEET)
        for section, fields in {'vocabulary': ('example',), 'grammar': ('pattern', 'example'), 'corrections': ('original', 'corrected'), 'conversation': ('question', 'answer')}.items():
            for item in sheet.get(section, []):
                for field in fields:
                    item[field + '_reading'] = 'いいてんきです。'
                    item[field + '_romaji'] = 'Ii tenki desu.'
        data = {'status':'completed', 'usage':USAGE, 'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(sheet or SHEET)}]}]}
        data.update(overrides)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(data).encode()
        return response

    @patch('core.services.study_notes.urlopen')
    def test_schema_timeout_usage_and_no_storage(self, api):
        api.return_value = self.response()
        with self.assertLogs('core.services.study_notes', level='INFO') as logs:
            content, tokens = request_study_note('ja','fr','A2',[])
        request = api.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(api.call_args.kwargs['timeout'],20)
        self.assertFalse(payload['store'])
        self.assertEqual(payload['max_output_tokens'],3600)
        self.assertTrue(payload['text']['format']['strict'])
        self.assertEqual(tokens,USAGE)
        self.assertNotIn('test-placeholder',''.join(logs.output))

    @patch('core.services.study_notes.urlopen')
    def test_unrecorded_corrections_are_removed(self, api):
        sheet=copy.deepcopy(SHEET)
        sheet['corrections']=[{'original':'bad','corrected':'good','explanation':'why','evidence':'mistake: bad was recorded'}]
        api.return_value=self.response(sheet)
        content,_=request_study_note('ja','fr','A2',[{'tutor_notes':{'what_we_talked_about':'Weather'},'private_notes':'mistake: bad was recorded'}])
        self.assertEqual(content['corrections'],[])
        content,_=request_study_note('ja','fr','A2',[{'tutor_notes':{'what_we_talked_about':'mistake: bad was recorded'}}])
        self.assertEqual(len(content['corrections']),1)

    @patch('core.services.study_notes.urlopen')
    def test_timeout_incomplete_refusal_and_malformed_responses(self, api):
        api.side_effect=TimeoutError
        with self.assertRaises(StudyGenerationError): request_study_note('ja','en','A1',[])
        api.side_effect=None
        for response in [self.response(status='incomplete'),self.response(output=[]),self.response({'title':'invalid'})]:
            api.return_value=response
            with self.assertRaises(StudyGenerationError): request_study_note('ja','en','A1',[])


class BeginnerReadingTests(TestCase):
    def sheet(self):
        sheet = copy.deepcopy(SHEET)
        sheet['vocabulary'][0].update(example_reading='いいてんきです。', example_romaji='Ii tenki desu.')
        sheet['conversation'][0].update(question_reading='ふゆがすきですか？', question_romaji='Fuyu ga suki desu ka?',
                                        answer_reading='はい、すきです。', answer_romaji='Hai, suki desu.')
        return sheet

    def test_a1_a2_and_unknown_require_complete_readings(self):
        for level in ['A1', 'A2', '']:
            schema = study_schema('ja', level)
            validate(self.sheet(), schema)
            validate_readings(self.sheet())
            with self.assertRaises(ValueError):
                validate(SHEET, schema)
        for target, level in [('ja','B1'), ('en','A1'), ('fr','A2'), ('es','A1')]:
            validate(SHEET, study_schema(target, level))

    def test_blank_or_kanji_readings_rejected(self):
        for value in ['', '冬が好きですか？']:
            sheet = self.sheet()
            sheet['conversation'][0]['question_reading'] = value
            with self.assertRaises(ValueError): validate_readings(sheet)
        sheet = self.sheet()
        sheet['conversation'][0]['answer_romaji'] = 'はい'
        with self.assertRaises(ValueError): validate_readings(sheet)

    def test_readings_render_and_legacy_notes_still_render(self):
        from django.template.loader import render_to_string
        from types import SimpleNamespace
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        note = SimpleNamespace(explanation_language='en', target_language='ja', learner_level='A1', source_lesson_ids=[], include_private_notes=False)
        context = {'note':note, 'sheet':self.sheet(), 'request':request}
        html = render_to_string('core/study_note_detail.html', context)
        for text in ['<ruby>天気<rt>てんき</rt></ruby>', 'いいてんきです。', 'Ii tenki desu.', 'ふゆがすきですか？', 'Fuyu ga suki desu ka?', 'Hai, suki desu.']:
            self.assertIn(text, html)
        context['sheet'] = SHEET
        self.assertIn('冬が好きですか？',render_to_string('core/study_note_detail.html',context))
        sheet = self.sheet()
        sheet['conversation'][0]['answer_romaji'] = '<script>alert(1)</script>'
        context['sheet'] = sheet
        html = render_to_string('core/study_note_detail.html',context)
        self.assertNotIn('<script>alert(1)</script>', html)


class ReviewQuizTests(TestCase):
    def quiz(self):
        return {'question': 'Choose the word for rain.', 'options': [
            {'text': t, 'reading': '', 'romaji': ''} for t in ['rain', 'sun', 'snow']],
            'correct_index': 0, 'explanation': 'Rain is falling water.', 'evidence': 'Practiced rain.'}

    @patch('core.services.study_notes.request_structured')
    @override_settings(OPENAI_API_KEY='test')
    def test_grounded_quiz_and_unrecorded_evidence(self, api):
        sheet = copy.deepcopy(SHEET)
        sheet['quiz'] = [self.quiz()]
        api.return_value = (sheet, USAGE)
        history = [{'tutor_notes': {'what_we_talked_about': 'Practiced rain.', 'level': 'A1', 'for_next_conversation': ''}}]
        content, _ = request_study_note('en', 'fr', 'A1', history)
        self.assertEqual(len(content['quiz']), 1)
        sheet['quiz'][0]['evidence'] = 'Invented lesson'
        content, _ = request_study_note('en', 'fr', 'A1', history)
        self.assertEqual(content['quiz'], [])

    def test_quiz_schema_rejects_invalid_answer_and_option_count(self):
        sheet = copy.deepcopy(SHEET)
        sheet['quiz'] = [self.quiz()]
        validate(sheet, study_schema('en', 'A1'))
        sheet['quiz'][0]['correct_index'] = 3
        with self.assertRaises(ValueError): validate(sheet, study_schema('en', 'A1'))
        sheet['quiz'][0]['correct_index'] = 0
        sheet['quiz'][0]['options'].pop()
        with self.assertRaises(ValueError): validate(sheet, study_schema('en', 'A1'))

    def test_render_answers_hidden_and_old_note_supported(self):
        from django.template.loader import render_to_string
        note = {'target_language': 'en', 'explanation_language': 'en'}
        sheet = copy.deepcopy(SHEET)
        sheet['quiz'] = [self.quiz()]
        html = render_to_string('core/study_note_detail.html', {'note': note, 'sheet': sheet})
        self.assertIn('quiz-feedback" hidden', html)
        self.assertIn('data-correct="0"', html)
        del sheet['quiz']
        html = render_to_string('core/study_note_detail.html', {'note': note, 'sheet': sheet})
        self.assertNotIn('id="quiz"', html)
