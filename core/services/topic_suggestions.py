"""Fresh conversation topics for tutors.

The learner brief only repeats what earlier notes recorded, so a learner who
once talked about lunch keeps getting lunch. These questions rotate with each
lesson so every tutor is offered topics the previous tutors were not.
"""

TOPICS = {
    'ja': [
        '週末は何をしましたか？', '仕事や勉強について教えてください。', '出身地はどんなところですか？',
        '最近行った旅行について教えてください。', '家族について教えてください。', '趣味は何ですか？',
        '好きな音楽や映画はありますか？', '今の季節に何をするのが好きですか？', '将来やってみたいことは何ですか？',
        '朝はいつも何をしますか？', '最近買ったものは何ですか？', '子どもの頃の思い出を教えてください。',
    ],
    'en': [
        'What did you do last weekend?', 'Tell me about your work or studies.', 'What is your hometown like?',
        'Tell me about a recent trip.', 'Tell me about your family.', 'What are your hobbies?',
        'What music or films do you like?', 'What do you like to do in this season?', 'What would you like to try in the future?',
        'What is your morning routine?', 'What is something you bought recently?', 'Tell me a childhood memory.',
    ],
    'fr': [
        "Qu'as-tu fait le week-end dernier ?", 'Parle-moi de ton travail ou de tes études.', "Comment est ta ville d'origine ?",
        'Raconte-moi un voyage récent.', 'Parle-moi de ta famille.', 'Quels sont tes loisirs ?',
        'Quelle musique ou quels films aimes-tu ?', "Qu'aimes-tu faire en cette saison ?", "Qu'aimerais-tu essayer à l'avenir ?",
        'Que fais-tu le matin ?', "Qu'as-tu acheté récemment ?", "Raconte-moi un souvenir d'enfance.",
    ],
    'es': [
        '¿Qué hiciste el fin de semana pasado?', 'Háblame de tu trabajo o tus estudios.', '¿Cómo es tu ciudad natal?',
        'Cuéntame sobre un viaje reciente.', 'Háblame de tu familia.', '¿Cuáles son tus aficiones?',
        '¿Qué música o películas te gustan?', '¿Qué te gusta hacer en esta estación?', '¿Qué te gustaría probar en el futuro?',
        '¿Qué haces por la mañana?', '¿Qué compraste recientemente?', 'Cuéntame un recuerdo de tu infancia.',
    ],
}


def fresh_topics(language_code, lessons_so_far, count=3):
    """Return `count` questions, moving on by `count` for every past lesson."""
    pool = TOPICS.get(language_code, TOPICS['en'])
    start = (lessons_so_far * count) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(count)]
