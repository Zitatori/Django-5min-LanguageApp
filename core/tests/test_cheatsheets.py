import copy
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import ConversationNote, StudyNote
from core.services.cheatsheets import (SCHEMA, AUDIT_SCHEMA, collect_context, generate_cheatsheet,
                                      validate_cheatsheet, text_blocks, allowed_topics)
from core.services.study_notes import StudyGenerationError, validate
from core.tests.test_study_notes import StudyNoteTests, USAGE


def text(value, kana='', romaji=''):
    return {'text': value, 'kana': kana, 'romaji': romaji}


def sample():
    return {'title': text('Two-day review'),
        'review': [{'content': text('Review weather.'), 'evidence': 'Weather'}],
        'vocabulary': [{'term': text('天気', 'てんき', 'tenki'), 'meaning': text('Weather'), 'evidence': 'Weather'}],
        'grammar': [],
        'practice': [{'prompt': text('Say weather.'), 'answer': text('天気', 'てんき', 'tenki')},
                     {'prompt': text('Say good weather.'), 'answer': text('いい天気です。', 'いいてんきです。', 'Ii tenki desu.')}],
        'next_steps': [{'topic_id': 'preferences', 'objective': text('Say which weather you like.'), 'reason': text('Build on weather vocabulary.')}],
    }


def stored():
    value = sample()
    for section in ('review', 'vocabulary', 'grammar'):
        for item in value[section]: item.pop('evidence')
    return value


@override_settings(LANGUAGE_CODE='en')
class CheatsheetTests(TestCase):
    setUp = StudyNoteTests.setUp
    lesson = StudyNoteTests.lesson

    def data(self, **changes):
        from core.views.study_notes import new_token
        data = {'lesson': self.match.pk, 'explanation_language': 'en', 'request_token': new_token(self.user)}
        data.update(changes)
        return data

    def post(self, **changes):
        return self.client.post(reverse('cheatsheets'), self.data(**changes))

    @patch('core.views.cheatsheets.generate_cheatsheet', return_value=(stored(), USAGE))
    def test_generate_duplicate_reload_links_and_expiry(self, api):
        response = self.post()
        self.assertEqual(response.status_code, 302)
        sheet = StudyNote.objects.get()
        self.assertEqual(sheet.lesson, self.match)
        self.assertEqual(sheet.learner_level, 'A2')
        self.assertEqual(sheet.format, 'cheatsheet')
        self.assertEqual(self.post().url, response.url)
        detail = self.client.get(response.url)
        self.assertContains(detail, 'tenki')
        self.assertContains(detail, '#lesson-' + str(self.match.pk))
        self.assertNotContains(detail, 'PRIVATE hobbies')
        self.assertNotContains(detail, 'private@example.com')
        self.assertNotContains(detail, 'evidence')
        self.assertContains(self.client.get(reverse('cheatsheets')), 'Two-day review')
        self.gold.delete()
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(self.client.get(reverse('study_note_detail', args=[sheet.pk])).url, response.url)

    @patch('core.views.cheatsheets.generate_cheatsheet')
    def test_missing_level_notes_future_and_foreign_lesson(self, api):
        ConversationNote.objects.filter(match=self.match).update(learner_level='')
        self.assertContains(self.post(), 'Your tutor needs')
        self.match.end_at = timezone.now() + timedelta(days=1); self.match.save()
        self.assertEqual(self.post().status_code, 400)
        self.match.end_at = timezone.now() - timedelta(minutes=1); self.match.save()
        self.client.force_login(self.other)
        self.assertEqual(self.post().status_code, 403)
        api.assert_not_called()

    @patch('core.views.cheatsheets.generate_cheatsheet', return_value=(stored(), USAGE))
    def test_owner_isolation_and_previous_next(self, api):
        first = self.post().url
        next_lesson = self.lesson(self.student)
        second = self.post(lesson=next_lesson.pk).url
        self.assertContains(self.client.get(first), second)
        self.assertContains(self.client.get(second), first)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(first).status_code, 404)
        self.client.force_login(self.tutor.user)
        self.assertEqual(self.client.get(first).status_code, 404)

    @patch('core.views.cheatsheets.generate_cheatsheet', side_effect=StudyGenerationError)
    def test_failure_releases_claim_and_safe_retry(self, api):
        self.assertContains(self.post(), 'could not create a verified')
        self.assertEqual(StudyNote.objects.get().status, 'failed')
        self.post()
        self.assertEqual(api.call_count, 2)

    @patch('core.views.cheatsheets.generate_cheatsheet')
    def test_shared_lock_and_database_duplicate_protection(self, api):
        StudyNote.objects.create(user=self.user, request_key=uuid.uuid4(), target_language='ja', explanation_language='en')
        self.assertEqual(self.post().status_code, 409)
        api.assert_not_called()
        StudyNote.objects.all().update(status='failed')
        StudyNote.objects.create(user=self.user, lesson=self.match, format='cheatsheet', status='ready',
            request_key=uuid.uuid4(), target_language='ja', explanation_language='en')
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudyNote.objects.create(user=self.user, lesson=self.match, format='cheatsheet', status='ready',
                request_key=uuid.uuid4(), target_language='ja', explanation_language='en')

    def test_context_does_not_use_student_private_notes_or_foreign_tutor(self):
        ctx = collect_context(self.user, self.match)
        self.assertNotIn('PRIVATE', str(ctx))
        self.assertNotIn('private@example.com', str(ctx))
        self.assertNotIn('Maria', str(ctx))
        self.assertEqual(ctx['level'], 'A2')
        ConversationNote.objects.filter(match=self.match).delete()
        self.assertIsNone(collect_context(self.user, self.match))

    @patch('core.views.cheatsheets.generate_cheatsheet', return_value=(stored(), USAGE))
    def test_multiple_lessons_no_monthly_limit_locales_and_csrf(self, api):
        for i in range(6):
            lesson = self.lesson(self.student)
            self.assertEqual(self.post(lesson=lesson.pk).status_code, 302)
        self.assertEqual(api.call_count, 6)
        for lang in ('ja', 'fr', 'en', 'es'):
            self.assertEqual(self.client.get(reverse('cheatsheets'), HTTP_ACCEPT_LANGUAGE=lang).status_code, 200)
        from django.test import Client
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(reverse('cheatsheets'), self.data()).status_code, 403)


class CheatsheetValidationTests(TestCase):
    def setUp(self):
        self.context = {'current': {'covered': 'Weather', 'next': '', 'level': 'A1'},
            'history': [], 'level': 'A1', 'previously_recommended': [], 'previous_coverage': []}

    def test_every_display_block_requires_full_readings(self):
        value = sample()
        validate_cheatsheet(value, self.context)
        for index, block in enumerate(list(text_blocks(value))):
            altered = copy.deepcopy(value)
            target = list(text_blocks(altered))[index]
            target.update(text='天気', kana='', romaji='')
            with self.assertRaises(ValueError): validate_cheatsheet(altered, self.context)

    def test_unsupported_evidence_advanced_grammar_duplicate_next(self):
        value = sample(); value['review'][0]['evidence'] = 'Invented'
        with self.assertRaises(ValueError): validate_cheatsheet(value, self.context)
        value = sample(); value['next_steps'][0]['topic_id'] = 'implication'
        with self.assertRaises(ValueError): validate_cheatsheet(value, self.context)
        value = sample(); value['next_steps'] *= 2
        with self.assertRaises(ValueError): validate_cheatsheet(value, self.context)
        self.assertNotIn('conditional', dict(allowed_topics('A1')))
        self.assertIn('conditional', dict(allowed_topics('B1')))
        with self.assertRaises(ValueError): validate({'no_private_details': 'yes'}, AUDIT_SCHEMA)

    @patch('core.services.cheatsheets.request_structured')
    def test_semantic_review_fail_closed_and_strip_evidence(self, api):
        audit = {key: True for key in AUDIT_SCHEMA['properties']}
        api.side_effect = [(sample(), USAGE.copy()), (audit, USAGE.copy())]
        value, usage = generate_cheatsheet('en', self.context)
        self.assertNotIn('evidence', str(value))
        self.assertEqual(usage['input_tokens'], 600)
        for key in audit:
            rejected = dict(audit, **{key: False})
            api.side_effect = [(sample(), USAGE.copy()), (rejected, USAGE.copy())]
            with self.assertRaises(StudyGenerationError): generate_cheatsheet('en', self.context)

    @patch('core.services.cheatsheets.request_structured')
    def test_reading_gap_never_reaches_second_call(self, api):
        value = sample(); value['practice'][1]['answer']['romaji'] = ''
        api.return_value = value, USAGE.copy()
        with self.assertRaises(StudyGenerationError): generate_cheatsheet('fr', self.context)
        self.assertEqual(api.call_count, 1)

    def test_explanation_schema_does_not_strip_japanese_readings(self):
        from core.services.cheatsheets import generation_schema
        schema = generation_schema('en', self.context)
        self.assertEqual(schema['properties']['title']['properties']['kana']['enum'], [''])
        term = schema['properties']['vocabulary']['items']['properties']['term']
        self.assertNotIn('enum', term['properties']['kana'])
        validate(sample(), schema)
        value = sample(); value['vocabulary'][0]['evidence'] = 'invented'
        with self.assertRaises(ValueError): validate(value, schema)

    def test_all_four_explanation_languages_have_independent_schema(self):
        from core.services.cheatsheets import generation_schema
        for lang in ('en', 'fr', 'es'):
            schema = generation_schema(lang, self.context)
            self.assertEqual(schema['properties']['title']['properties']['romaji']['enum'], [''])
        schema = generation_schema('ja', self.context)
        self.assertNotIn('enum', schema['properties']['title']['properties']['romaji'])

    def test_control_characters_and_escaped_unicode_rejected(self):
        for bad in ('weather\x16', r'weather \u5929'):
            value = sample(); value['review'][0]['content']['text'] = bad
            with self.assertRaises(ValueError): validate_cheatsheet(value, self.context)
