import json
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.utils import timezone


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.room_group_name = f'lesson_{self.match_id}'
        self.authorized = False
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4403)
            return
        self.user_id = user.pk
        self.role = await self._role()
        if not self.role:
            await self.close(code=4403)
            return
        self.authorized = True
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if not getattr(self, 'authorized', False):
            return
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.channel_layer.group_send(self.room_group_name, {
            'type':'send_signal', 'message':{'type':'peer_left'}, 'sender_channel_name':self.channel_name})

    async def receive(self, text_data):
        if not self.authorized or len(text_data) > 64000:
            return
        try:
            data = json.loads(text_data)
        except (ValueError, TypeError):
            return
        if not isinstance(data, dict):
            return
        kind = data.get('type')
        if kind in ('webrtc_connected', 'media_heartbeat'):
            message = await self._media_ready()
            if message:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type':'send_signal', 'message':message, 'sender_channel_name':''})
            return
        if kind not in ('join', 'offer', 'answer', 'ice-candidate', 'camera_state'):
            return
        data['sender'] = self.user_id
        await self.channel_layer.group_send(self.room_group_name, {
            'type':'send_signal', 'message':data, 'sender_channel_name':self.channel_name})

    async def send_signal(self, event):
        if event['sender_channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def _role(self):
        from core.models import QuickLessonMatch
        from core.services.lesson_lifecycle import active_calls
        match = QuickLessonMatch.objects.filter(pk=self.match_id).filter(active_calls()).select_related('request__student', 'tutor').first()
        if not match:
            return None
        if match.request.student.user_id == self.user_id:
            return 'student'
        if match.tutor.user_id == self.user_id:
            return 'tutor'
        return None

    @database_sync_to_async
    def _media_ready(self):
        from core.models import QuickLessonMatch, TutorProfile
        from core.services.lesson_lifecycle import active_calls, settle_points
        now = timezone.now()
        with transaction.atomic():
            match = QuickLessonMatch.objects.select_for_update().filter(pk=self.match_id).filter(active_calls(now)).first()
            if not match:
                return None
            field = self.role + '_media_at'
            setattr(match, field, now)
            match.save(update_fields=[field])
            if self.role == 'tutor':
                TutorProfile.objects.filter(pk=match.tutor_id).update(last_ping_at=now)
            if not (match.student_media_at and match.tutor_media_at and match.student_joined_at and match.tutor_joined_at):
                return None
            if (now-min(match.student_media_at, match.tutor_media_at)).total_seconds() > 15:
                return None
            if not match.started_at:
                match.started_at = now
                match.end_at = now + timedelta(minutes=5)
                match.save(update_fields=['started_at', 'end_at'])
        settle_points(self.match_id, now)
        return {'type':'timer_start', 'seconds':max(0, int((match.end_at-now).total_seconds())), 'end_at':match.end_at.isoformat()}
