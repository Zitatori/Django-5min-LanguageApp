"""Private, persisted study materials and database-backed generation claims."""
import uuid
from django.conf import settings
from django.db import models


class StudyNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_notes')
    request_key = models.UUIDField()
    format = models.CharField(max_length=20, default='study_note')
    lesson = models.ForeignKey('QuickLessonMatch', null=True, blank=True,
        on_delete=models.CASCADE, related_name='study_cheatsheets')
    target_language = models.CharField(max_length=2)
    explanation_language = models.CharField(max_length=2)
    include_private_notes = models.BooleanField(default=False)
    learner_level = models.CharField(max_length=2, blank=True)
    source_lesson_ids = models.JSONField(default=list)
    content = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='generating', choices=[('generating', 'Generating'), ('ready', 'Ready'), ('failed', 'Failed')])
    model = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'lesson'],
                condition=models.Q(format='cheatsheet', status__in=['generating', 'ready']),
                name='cheatsheet_once_per_lesson'),
            models.UniqueConstraint(fields=['user', 'request_key'], name='study_request_once'),
            models.UniqueConstraint(fields=['user'], condition=models.Q(status='generating'), name='study_one_generation_per_user'),
        ]
