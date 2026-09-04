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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.tutor} for {self.student} on {self.created_at:%Y-%m-%d}"
