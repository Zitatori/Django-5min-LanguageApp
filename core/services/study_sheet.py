"""Presentation only: saved content and owner-scoped lesson records, never an API call."""
from core.models import ConversationNote
from core.services.note_translation import source_hash


def sheet_records(note):
    ids = [value for value in note.source_lesson_ids if isinstance(value, int)]
    if not ids and note.lesson_id:
        ids = [note.lesson_id]
    records = ConversationNote.objects.filter(
        match_id__in=ids, student__user_id=note.user_id,
        match__request__student__user_id=note.user_id,
        conversation_not_held=False,
    ).select_related('match', 'tutor__user').prefetch_related('translations').order_by('match__end_at', 'pk')
    result = []
    for record in records:
        translation = next((row.content for row in record.translations.all()
            if row.language == note.explanation_language and row.status == 'ready'
            and row.fingerprint == source_hash(record)), {})
        result.append({'note': record, 'translation': translation})
    return result
