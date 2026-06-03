from django.db import models
from django.contrib.auth.models import User

from .languages import LessonLanguage


class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    TUTOR = "tutor", "Tutor"
    ADMIN = "admin", "Admin"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )


class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    languages = models.ManyToManyField(LessonLanguage, blank=True)
    is_online = models.BooleanField(default=False)
    can_interview = models.BooleanField(default=False)
    last_ping_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Tutor: {self.user.username}"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    native_language = models.ForeignKey(
        LessonLanguage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self) -> str:
        return f"Student: {self.user.username}"
    