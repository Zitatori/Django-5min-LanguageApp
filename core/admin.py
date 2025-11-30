from django.contrib import admin
from .models import (
    LessonLanguage,
    TutorProfile,
    StudentProfile,
    QuickLessonRequest,
    QuickLessonMatch,
)


@admin.register(LessonLanguage)
class LessonLanguageAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_online")
    list_filter = ("is_online",)
    filter_horizontal = ("languages",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "native_language")


@admin.register(QuickLessonRequest)
class QuickLessonRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "language", "status", "created_at")
    list_filter = ("status", "language")
    search_fields = ("student__user__username",)


@admin.register(QuickLessonMatch)
class QuickLessonMatchAdmin(admin.ModelAdmin):
    list_display = ("id", "student_name", "tutor_name", "started_at", "end_at", "price")
    search_fields = ("request__student__user__username", "tutor__user__username")
