from django.db import models

from .languages import LessonLanguage
from .users import StudentProfile, TutorProfile


class QuickLessonRequest(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("matched", "Matched"),
        ("cancelled", "Cancelled"),
    ]

    PURPOSE_CHOICES = [
        ("lesson", "Lesson"),
        ("interview", "Interview"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    language = models.ForeignKey(LessonLanguage, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="waiting",
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default="lesson",
    )

    def __str__(self) -> str:
        return f"Request#{self.id}({self.purpose}) by {self.student.user.username}"


class QuickLessonMatch(models.Model):
    request = models.OneToOneField(QuickLessonRequest, on_delete=models.CASCADE)
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE)

    student_joined_at = models.DateTimeField(null=True, blank=True)
    tutor_joined_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    meeting_url = models.URLField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    def __str__(self) -> str:
        return f"Match#{self.id} {self.student_name} x {self.tutor_name}"

    @property
    def student_name(self) -> str:
        return self.request.student.user.username

    @property
    def tutor_name(self) -> str:
        return self.tutor.user.username