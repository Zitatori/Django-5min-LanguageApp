import re
import subprocess
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override
from core.tests.test_call_lifecycle import CallFixture
from core.views.student import active_tutors_qs

class TutorPresenceTests(CallFixture, TestCase):
    def test_cancelled_match_releases_on_uncached_heartbeat(self):
        self.request.status='cancelled';self.request.save()
        self.match.end_at=self.now;self.match.save()
        self.tutor.is_online=False;self.tutor.save()
        self.client.force_login(self.tutor.user)
        response=self.client.get(reverse('tutor_match_status'))
        self.assertFalse(response.json()['matched'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertIn(self.tutor,active_tutors_qs(self.language))

    def test_dashboard_no_cache_and_valid_scripts_in_four_languages(self):
        self.client.force_login(self.tutor.user)
        for lang in ('ja','en','fr','es'):
            with override(lang):
                response=self.client.get(reverse('tutor_dashboard'),HTTP_ACCEPT_LANGUAGE=lang)
            self.assertIn('no-store',response['Cache-Control'])
            self.assertContains(response,'presence-error')
            for script in re.findall(r'<script>(.*?)</script>',response.content.decode(),re.S):
                checked=subprocess.run(['node','--check'],input=script,text=True,capture_output=True)
                self.assertEqual(checked.returncode,0,checked.stderr)
