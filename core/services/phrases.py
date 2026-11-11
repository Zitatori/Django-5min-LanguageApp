from django.utils.translation import gettext as _


def conversation_phrases(language, level):
    """Small static learner aid; never requires an AI request."""
    meanings = [_('Please say that again.'), _('Please speak slowly.'), _("I don’t understand."), _('How about you?'), _('My name is …'), _('I like …')]
    phrases = {
        'ja': [('もう一度お願いします。', 'Mō ichido onegai shimasu.'), ('ゆっくり話してください。', 'Yukkuri hanashite kudasai.'), ('分かりません。', 'Wakarimasen.'), ('あなたはどうですか？', 'Anata wa dō desu ka?'), ('私の名前は…です。', 'Watashi no namae wa … desu.'), ('…が好きです。', '… ga suki desu.')],
        'en': [('Please say that again.', '/pliːz seɪ ðæt əˈɡen/'), ('Please speak slowly.', '/pliːz spiːk ˈsləʊli/'), ('I don’t understand.', '/aɪ dəʊnt ˌʌndəˈstænd/'), ('How about you?', '/haʊ əˈbaʊt juː/'), ('My name is …', '/maɪ neɪm ɪz/'), ('I like …', '/aɪ laɪk/')],
        'fr': [('Pouvez-vous répéter, s’il vous plaît ?', '/puve vu ʁepete sil vu plɛ/'), ('Parlez lentement, s’il vous plaît.', '/paʁle lɑ̃tmɑ̃ sil vu plɛ/'), ('Je ne comprends pas.', '/ʒə nə kɔ̃pʁɑ̃ pa/'), ('Et vous ?', '/e vu/'), ('Je m’appelle …', '/ʒə mapɛl/'), ('J’aime …', '/ʒɛm/')],
        'es': [('¿Puede repetir, por favor?', '/ˈpwede repeˈtiɾ poɾ faˈβoɾ/'), ('Hable despacio, por favor.', '/ˈaβle desˈpaθjo poɾ faˈβoɾ/'), ('No entiendo.', '/no enˈtjendo/'), ('¿Y usted?', '/i usˈteð/'), ('Me llamo …', '/me ˈʝamo/'), ('Me gusta …', '/me ˈɣusta/')],
    }
    if level not in ('', 'A1'):
        meanings[-1] = _('I like … because …')
        extended = {'ja': ('…が好きです。理由は…です。', '… ga suki desu. Riyū wa … desu.'), 'en': ('I like … because …', '/aɪ laɪk/ … /bɪˈkɒz/ …'), 'fr': ('J’aime … parce que …', '/ʒɛm/ … /paʁs kə/ …'), 'es': ('Me gusta … porque …', '/me ˈɣusta/ … /ˈpoɾke/ …')}
        if language in extended:
            phrases[language][-1] = extended[language]
    # Familiar pronunciation hints for Japanese-speaking beginners.
    from django.utils.translation import get_language
    if (get_language() or '').startswith('ja') and language != 'ja':
        hints = {
            'en': ['プリーズ セイ ザット アゲン', 'プリーズ スピーク スロウリー', 'アイ ドウント アンダスタンド', 'ハウ アバウト ユー', 'マイ ネイム イズ …', 'アイ ライク …'],
            'fr': ['プヴェ ヴ レペテ スィル ヴ プレ', 'パルレ ラントマン スィル ヴ プレ', 'ジュ ヌ コンプラン パ', 'エ ヴ', 'ジュ マペル …', 'ジェム …'],
            'es': ['プエデ レペティール ポル ファボール', 'アブレ デスパシオ ポル ファボール', 'ノ エンティエンド', 'イ ウステ', 'メ ジャモ …', 'メ グスタ …'],
        }
        if language in hints:
            if level not in ('', 'A1'):
                hints[language][-1] += {'en': ' ビコーズ …', 'fr': ' パルス ク …', 'es': ' ポルケ …'}[language]
            phrases[language] = [(text, hint) for (text, _reading), hint in zip(phrases[language], hints[language])]
    return [(text, reading, meaning) for (text, reading), meaning in zip(phrases.get(language, []), meanings)]
