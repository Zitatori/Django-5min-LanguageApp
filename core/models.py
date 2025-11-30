from django.db import models
from django.contrib.auth.models import User


# models.py に追加（別モデルでもいい）
class UserRole(models.TextChoices):
    STUDENT = "student", "Student"
    TUTOR = "tutor", "Tutor"
    ADMIN = "admin", "Admin"


# User を直接拡張する代わりに、拡張プロフィールを作る案もあり
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )

class LessonLanguage(models.Model):
    code = models.CharField(max_length=10, unique=True)  # 'en', 'es', 'ja'
    name = models.CharField(max_length=50)               # English, Español, 日本語

    def __str__(self) -> str:
        return self.name


class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    languages = models.ManyToManyField(LessonLanguage, blank=True)
    is_online = models.BooleanField(default=False)

    # ここを追加：アドミン的な講師（面接担当もできる）かどうか
    can_interview = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Tutor: {self.user.username}"



class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    native_language = models.ForeignKey(
        LessonLanguage, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self) -> str:
        return f"Student: {self.user.username}"


class QuickLessonRequest(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("matched", "Matched"),
        ("cancelled", "Cancelled"),
    ]

    PURPOSE_CHOICES = [
        ("lesson", "Lesson"),        # 普通の5分レッスン
        ("interview", "Interview"),  # 講師候補との面接
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    language = models.ForeignKey(LessonLanguage, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="waiting"
    )

    # ここを追加：このリクエストが「レッスン」なのか「面接」なのか
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
    started_at = models.DateTimeField()
    end_at = models.DateTimeField()
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
