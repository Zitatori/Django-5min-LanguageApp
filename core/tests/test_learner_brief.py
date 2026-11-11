import json
from unittest.mock import patch, MagicMock
from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from core.models import ConversationNote, LessonLanguage, QuickLessonRequest, QuickLessonMatch
from core.services.learner_brief import get_or_generate_brief, request_brief
from core.tests.test_conversation_notes import ConversationNotesTests

@override_settings(OPENAI_API_KEY='test-only')
class LearnerBriefTests(ConversationNotesTests):
    def test_all_history_scoped_cached_and_no_private_notes(self):
        for i in range(7):
            ConversationNote.objects.create(student=self.match.request.student,tutor=self.tutor,match=self.match,talked_about='Topic '+str(i))
        other=LessonLanguage.objects.create(code='fr',name='French')
        m=QuickLessonMatch.objects.create(tutor=self.tutor,request=QuickLessonRequest.objects.create(student=self.match.request.student,language=other))
        ConversationNote.objects.create(student=self.match.request.student,tutor=self.tutor,match=m,talked_about='excluded')
        ConversationNote.objects.create(student=self.match.request.student,tutor=self.tutor,match=self.match,talked_about='not held',conversation_not_held=True)
        args=(self.match.request.student_id,self.match.request.language_id,'English')
        with patch('core.services.learner_brief.request_brief',return_value=[{'text':'Topic','date':'2026-01-01','source_id':1}]) as api:
            self.assertEqual(get_or_generate_brief(*args)['status'],'ready')
            self.assertEqual(get_or_generate_brief(*args)['status'],'ready')
        api.assert_called_once()
        history=api.call_args.args[1]
        self.assertEqual(len(history),7)
        self.assertEqual(history[0]['content'],'Topic 0')
        self.assertEqual(set(history[0]),{'id','date','content'})

    def test_permissions_and_failure(self):
        ConversationNote.objects.create(student=self.match.request.student,tutor=self.tutor,match=self.match,talked_about='Hiking')
        url=reverse('learner_brief',args=[self.match.pk])
        with patch('core.services.learner_brief.request_brief',side_effect=ValueError) as api:
            self.assertEqual(self.client.post(url).json()['status'],'unavailable')
            self.client.post(url)
            api.assert_called_once()
        self.client.force_login(self.match.request.student.user)
        self.assertEqual(self.client.post(url).status_code,404)

    def test_save_no_longer_generates_questions(self):
        with patch('core.services.question_generation.request_questions') as api:
            self.client.post(self.url,{'talked_about':'Hiking','learner_level':'A1','next_conversation':'Past tense'})
        api.assert_not_called()
        self.assertEqual(ConversationNote.objects.get(match=self.match).questions_status,'retired')

class BriefValidationTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY='test-only',OPENAI_QUESTION_MODEL='gpt-4.1-mini')
    def test_evidence_and_structured_request(self):
        for evidence,valid in [('Likes films',True),('Invented',False)]:
            response=MagicMock()
            response.read.return_value=json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'facts':[{'text':'Enjoys films','source_id':1,'evidence':evidence}]})}]}]}).encode()
            with patch('core.services.learner_brief.urlopen') as transport:
                transport.return_value.__enter__.return_value=response
                if valid:
                    result=request_brief('English',[{'id':1,'date':'2026-01-01','content':'Likes films'}])
                    self.assertEqual(result[0]['date'],'2026-01-01')
                    self.assertFalse(json.loads(transport.call_args.args[0].data)['store'])
                else:
                    with self.assertRaises(ValueError):
                        request_brief('English',[{'id':1,'date':'2026-01-01','content':'Likes films'}])

class BriefRoomTests(ConversationNotesTests):
    def test_room_shows_brief_and_history_not_old_questions(self):
        ConversationNote.objects.create(student=self.match.request.student,tutor=self.tutor,match=self.match,
            talked_about='Likes hiking',suggested_questions=['Old generated question?'])
        with patch('core.services.learner_brief.request_brief') as api:
            response=self.client.get(reverse('lesson_room',args=[self.match.pk]))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'learner-brief-facts')
        self.assertContains(response,'Likes hiking')
        self.assertNotContains(response,'Old generated question?')
        api.assert_not_called()
