from django.test import SimpleTestCase
from django.template.loader import render_to_string
from django.utils.translation import override
from core.services.phrases import conversation_phrases


class StarterPhraseTests(SimpleTestCase):
    def test_all_languages_levels_have_six_readings_and_translations(self):
        for ui in ['ja', 'en', 'fr', 'es']:
            with override(ui):
                for target in ['ja', 'en', 'fr', 'es']:
                    for level in ['', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
                        phrases = conversation_phrases(target, level)
                        self.assertEqual(len(phrases), 6)
                        self.assertTrue(all(all(row) for row in phrases))
                        html = render_to_string('core/_starter_phrases.html', {'conversation_phrases': phrases})
                        self.assertEqual(html.count('class="starter-item"'), 6)

    def test_level_and_ui_language(self):
        with override('ja'):
            beginner = conversation_phrases('en', 'A1')
            self.assertIn('プリーズ', beginner[0][1])
            self.assertEqual(beginner[-1][0], 'I like …')
            self.assertIn('because', conversation_phrases('en', 'A2')[-1][0])
        with override('fr'):
            japanese = conversation_phrases('ja', 'A1')
            self.assertEqual(japanese[2][1], 'Wakarimasen.')
            self.assertEqual(japanese[4][2], 'Je m’appelle …')
        self.assertEqual(conversation_phrases('unknown', 'A1'), [])
