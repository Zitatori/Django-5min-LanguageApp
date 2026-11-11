from django.db import models
from .users import StudentProfile, TutorProfile
from .lessons import QuickLessonMatch


class ConversationNote(models.Model):
    LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
        ("C1", "C1"),
        ("C2", "C2"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="conversation_notes")
    tutor   = models.ForeignKey(TutorProfile,   on_delete=models.CASCADE, related_name="conversation_notes")
    match   = models.ForeignKey(QuickLessonMatch, on_delete=models.SET_NULL, null=True, blank=True)
    note    = models.TextField(max_length=500)
    learner_level = models.CharField(max_length=2, choices=LEVEL_CHOICES, blank=True, default="")
    talked_about = models.TextField(max_length=500, blank=True, default="")
    next_conversation = models.TextField(max_length=500, blank=True, default="")
    conversation_not_held = models.BooleanField(default=False)
    learner_brief = models.JSONField(default=list, blank=True)
    brief_fingerprint = models.CharField(max_length=64, blank=True, default="")
    brief_attempted_at = models.DateTimeField(null=True, blank=True)
    suggested_questions = models.JSONField(default=list, blank=True)
    questions_status = models.CharField(max_length=16, default="pending")
    questions_level = models.CharField(max_length=2, blank=True, default="")
    questions_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def conversation_content(self):
        """Show conversation content while preserving legacy free-form notes."""
        if self.talked_about:
            return self.talked_about
        if self.learner_level or self.next_conversation:
            return ""
        return self.note

    def __str__(self):
        return f"Note by {self.tutor} for {self.student} on {self.created_at:%Y-%m-%d}"


class LessonNoteTranslation(models.Model):
    note = models.ForeignKey(ConversationNote, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=2)
    fingerprint = models.CharField(max_length=64, default='')
    content = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='pending')
    attempted_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['note', 'language'], name='lesson_translation_language')]
