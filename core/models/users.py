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
    referral_source = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )
    is_starred = models.BooleanField(default=False)


class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    languages = models.ManyToManyField(LessonLanguage, blank=True)
    is_online = models.BooleanField(default=False)
    can_interview = models.BooleanField(default=False)
    is_hourly_paid = models.BooleanField(default=False)
    last_ping_at = models.DateTimeField(null=True, blank=True)
    online_since = models.DateTimeField(null=True, blank=True)

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


class LearnerLanguageLevel(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='language_levels')
    language = models.ForeignKey(LessonLanguage, on_delete=models.CASCADE)
    level = models.CharField(max_length=2, choices=[(x, x) for x in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['student', 'language'], name='one_self_level_per_language')]
