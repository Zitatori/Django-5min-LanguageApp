from django.urls import path
from . import views
from .views import VideoRoomView
from core.views.admin import admin_dashboard, update_tutor_languages




urlpatterns = [
    path("", views.home, name="home"),
    path("request/", views.create_request, name="create_request"),
    path("match/<int:request_id>/", views.request_detail, name="request_detail"),
    path("tutor/dashboard/", views.tutor_dashboard, name="tutor_dashboard"),
    path("interview/request/", views.create_interview_request, name="create_interview_request"),
    path("video-room/", VideoRoomView.as_view(), name="video_room"),
    path("signup/", views.signup, name="signup"),
    path("history/", views.student_history, name="student_history"),
    path("tutor/match-status/", views.tutor_match_status, name="tutor_match_status"),

    # レッスンルーム
    path("lesson/room/<int:match_id>/", views.lesson_room, name="lesson_room"),

    #アドミンページ
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/tutor/<int:tutor_id>/languages/', update_tutor_languages, name='update_tutor_languages'),
]
