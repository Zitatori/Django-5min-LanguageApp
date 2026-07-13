from .home import home, privacy
from .student import create_request, request_detail, create_interview_request, student_history, student_online_counts, request_admin_chat
from .tutor import tutor_dashboard, tutor_match_status, tutor_set_offline
from .lesson import lesson_room, lesson_end, lesson_rating, video_room, VideoRoomView
from .auth import signup
from core.views.admin import admin_dashboard, update_tutor_languages
