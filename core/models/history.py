from django.db import models
from django.conf import settings


class LessonHistory(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_histories_as_student"
    )
    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_histories_as_tutor"
    )
    language = models.ForeignKey(
        "LessonLanguage",
        on_delete=models.PROTECT
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.tutor} - {self.language}"