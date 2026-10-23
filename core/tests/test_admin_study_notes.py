import uuid
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from core.models import StudyNote, UserProfile
from core.tests.test_study_notes import SHEET
from core.tests.test_cheatsheets import stored


@override_settings(LANGUAGE_CODE='en')
class AdminStudyNotesTests(TestCase):
    def setUp(self):
        self.learner = User.objects.create_user('learner')
        self.other = User.objects.create_user('other')
        self.admin = User.objects.create_user('admin', is_staff=True)
        self.note = StudyNote.objects.create(user=self.learner, request_key=uuid.uuid4(),
            target_language='ja', explanation_language='en', status='ready', content=SHEET)
        self.list_url = reverse('admin_study_notes', args=[self.learner.pk])
        self.detail_url = reverse('admin_study_note_detail', args=[self.learner.pk, self.note.pk])

    def test_anonymous_and_non_admin_denied(self):
        for url in (self.list_url, self.detail_url):
            self.assertEqual(self.client.get(url).status_code, 302)
        for user in (self.learner, self.other):
            self.client.force_login(user)
            for url in (self.list_url, self.detail_url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_list_detail_and_read_only(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.list_url), self.detail_url)
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'Weather review')
        self.assertContains(response, 'Read-only administrator view')
        self.assertIn('no-store', response['Cache-Control'])
        for url in (self.list_url, self.detail_url):
            self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(StudyNote.objects.count(), 1)

    def test_admin_role_supported_owner_mismatch_and_failed_not_found(self):
        UserProfile.objects.update_or_create(user=self.other, defaults={'role': 'Admin'})
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin_study_note_detail', args=[self.other.pk, self.note.pk])).status_code, 404)
        self.note.status = 'failed'; self.note.save()
        self.assertEqual(self.client.get(self.detail_url).status_code, 404)
        self.assertNotContains(self.client.get(self.list_url), self.detail_url)

    def test_cheatsheet_renderer_and_owner_endpoint_unchanged(self):
        self.note.format = 'cheatsheet'; self.note.content = stored(); self.note.save()
        self.client.force_login(self.admin)
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'tenki')
        self.assertNotContains(response, 'href="/history/')
        self.assertEqual(self.client.get(reverse('cheatsheet_detail', args=[self.note.pk])).status_code, 404)

    def test_saved_evidence_is_not_shown_to_admin(self):
        self.note.content = dict(SHEET, corrections=[{'original':'bad','corrected':'good','explanation':'Example',
            'evidence':'RAW TUTOR PRIVATE EVIDENCE'}])
        self.note.save(); self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(self.detail_url), 'RAW TUTOR PRIVATE EVIDENCE')
