from django.urls import path
from . import views
from .views import VideoRoomView
from core.views.admin import admin_dashboard, update_tutor_languages, update_user_languages, delete_user, update_user_points, grant_initial_points_all, process_withdrawal, grant_gold
from core.views.profile import profile, purchase_points, request_withdrawal, request_gold




urlpatterns = [
    path("", views.home, name="home"),
    path("privacy/", views.privacy, name="privacy"),
    path("request/", views.create_request, name="create_request"),
    path("request/online-counts/", views.student_online_counts, name="student_online_counts"),
    path("match/<int:request_id>/", views.request_detail, name="request_detail"),
    path("tutor/dashboard/", views.tutor_dashboard, name="tutor_dashboard"),
    path("interview/request/", views.create_interview_request, name="create_interview_request"),
    path("video-room/", VideoRoomView.as_view(), name="video_room"),
    path("signup/", views.signup, name="signup"),
    path("history/", views.student_history, name="student_history"),
    path("tutor/match-status/", views.tutor_match_status, name="tutor_match_status"),
    path("tutor/set-offline/", views.tutor_set_offline, name="tutor_set_offline"),

    # レッスンルーム
    path("lesson/room/<int:match_id>/", views.lesson_room, name="lesson_room"),
    path("lesson/room/<int:match_id>/end/", views.lesson_end, name="lesson_end"),

    #アドミンページ
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/tutor/<int:tutor_id>/languages/', update_tutor_languages, name='update_tutor_languages'),
    path('admin-dashboard/user/<int:user_id>/languages/', update_user_languages, name='update_user_languages'),
    path('admin-dashboard/user/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('admin-dashboard/user/<int:user_id>/points/', update_user_points, name='update_user_points'),
    path('admin-dashboard/grant-initial-points/', grant_initial_points_all, name='grant_initial_points_all'),

    # プロフィール・ポイント
    path('profile/', profile, name='profile'),
    path('points/purchase/', purchase_points, name='purchase_points'),
    path('points/withdraw/', request_withdrawal, name='request_withdrawal'),

    # 引き出し申請処理（admin用）
    path('admin-dashboard/withdrawal/<int:withdrawal_id>/', process_withdrawal, name='process_withdrawal'),

    # Gold メンバーシップ
    path('gold/request/', request_gold, name='request_gold'),
    path('admin-dashboard/user/<int:user_id>/grant-gold/', grant_gold, name='grant_gold'),
]
