from django.urls import path
from .consumers import VideoCallConsumer

websocket_urlpatterns = [
    path("ws/lesson/<int:match_id>/", VideoCallConsumer.as_asgi()),
]