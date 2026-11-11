from datetime import date
from django.test import SimpleTestCase
from django.utils.translation import override, gettext, ngettext
from django.utils.formats import date_format
from core.services.study_display import localized_study_content

class FrenchCopyTests(SimpleTestCase):
    def test_labels_and_plural_and_date(self):
        with override('fr'):
            expected = {'Japanese':'Japonais', 'online':'en ligne', 'Total lessons':'Nombre de leçons', 'Gold member':'Membre Gold', 'Active until':'Valable jusqu’au', 'Select the language and tutor you want to practice with.':'Choisissez la langue et le tuteur avec qui vous souhaitez pratiquer.', 'No tutors online for this language.':'Aucun tuteur en ligne pour cette langue pour le moment.', 'Lesson #%(number)s':'Leçon n° %(number)s'}
            for key,value in expected.items():
                self.assertEqual(gettext(key),value)
            self.assertEqual(ngettext('%(n)s lesson','%(n)s lessons',1) % {'n':1}, '1 leçon')
            self.assertEqual(date_format(date(2026,12,4),'DATE_FORMAT'),'4 décembre 2026')

    def test_saved_content_not_mutated_and_other_languages_unchanged(self):
        old={'grammar':[{'pattern':'Questions en W'}]}
        result=localized_study_content(old,'fr')
        self.assertEqual(result['grammar'][0]['pattern'],'Questions avec où, quand, combien de temps')
        self.assertEqual(old['grammar'][0]['pattern'],'Questions en W')
        self.assertEqual(localized_study_content(old,'en'),old)
