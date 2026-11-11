"""Read-only: identify records needing human review; never delete or refund."""
import json
from django.core.management.base import BaseCommand
from core.models import QuickLessonMatch, PointTransaction


class Command(BaseCommand):
    help = 'Report suspect call IDs and transaction counts without changing data.'

    def handle(self, *args, **options):
        for match in QuickLessonMatch.objects.all().iterator():
            reasons = []
            if match.end_at and (not match.started_at or (match.end_at-match.started_at).total_seconds() < 1):
                reasons.append('no_positive_connected_duration')
            if match.end_at and (not match.student_joined_at or not match.tutor_joined_at):
                reasons.append('missing_participant')
            if match.conversationnote_set.filter(conversation_not_held=True).exists():
                reasons.append('tutor_marked_not_held')
            if reasons:
                transactions = PointTransaction.objects.filter(reference_id=match.pk, transaction_type__in=['lesson_taken','lesson_taught'])
                self.stdout.write(json.dumps({'match_id':match.pk, 'reasons':reasons, 'point_transaction_count':transactions.count()}))
