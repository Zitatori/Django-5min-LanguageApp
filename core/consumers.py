import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache

POINTS_DELAY_SECONDS = 60  # レッスン開始からこの秒数後にポイント処理


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_id = self.scope["url_route"]["kwargs"]["match_id"]
        self.room_group_name = f"lesson_{self.match_id}"
        user = self.scope.get("user")
        self.user_id = str(user.id) if user and user.is_authenticated else self.channel_name
        self.has_joined = False

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # 退室時にユニークな入室ユーザーから外す。
        # 再接続やjoin再送で人数カウントがずれないよう、単純なjoin回数では数えない。
        users_key = f"room_users_{self.match_id}"
        users = set(cache.get(users_key, []))
        if self.has_joined:
            users.discard(self.user_id)
            cache.set(users_key, list(users), timeout=3600)

        # 相手に「退室した」シグナルを送る
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "send_signal",
                "message": {"type": "peer_left"},
                "sender_channel_name": "",
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "join":
            users_key = f"room_users_{self.match_id}"
            users = set(cache.get(users_key, []))
            users.add(self.user_id)
            self.has_joined = True
            cache.set(users_key, list(users), timeout=3600)
            count = len(users)
            print(f"[ws] match={self.match_id} join users={count} ch={self.channel_name[:8]}")

            timer_message = await self._timer_start_message()
            if timer_message:
                # 2人ともレッスンルームに入室済み → タイマー開始
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_signal",
                        "message": timer_message,
                        "sender_channel_name": "",
                    }
                )
                print(f"[ws] match={self.match_id} → timer_start sent")
                # 60秒後にポイント処理（このインスタンスが担当、二重防止はcacheロック）
                asyncio.ensure_future(self._schedule_points())

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "send_signal",
                "message": data,
                "sender_channel_name": self.channel_name,
            }
        )

    async def send_signal(self, event):
        if event["sender_channel_name"] and event["sender_channel_name"] == self.channel_name:
            return
        await self.send(text_data=json.dumps(event["message"]))

    # ──────────────────────────────────────────
    # ポイント処理
    # ──────────────────────────────────────────

    async def _schedule_points(self):
        await asyncio.sleep(POINTS_DELAY_SECONDS)
        await self._process_lesson_points()

    @database_sync_to_async
    def _timer_start_message(self):
        from core.models import QuickLessonMatch
        from django.utils import timezone

        match = QuickLessonMatch.objects.filter(
            id=self.match_id,
            student_joined_at__isnull=False,
            tutor_joined_at__isnull=False,
        ).first()
        if not match:
            return None

        if not match.started_at or not match.end_at:
            now = timezone.now()
            QuickLessonMatch.objects.filter(pk=match.pk, started_at__isnull=True).update(
                started_at=now,
                end_at=now + timezone.timedelta(minutes=5),
            )
            match.refresh_from_db()

        seconds = max(0, int((match.end_at - timezone.now()).total_seconds()))
        return {
            "type": "timer_start",
            "seconds": seconds,
            "end_at": match.end_at.isoformat(),
        }

    @database_sync_to_async
    def _process_lesson_points(self):
        """cacheロックで二重処理を防ぎながら student -1pt / tutor +1pt を確定"""
        lock_key = f"points_done_{self.match_id}"
        if cache.get(lock_key):
            return  # 既に処理済み
        cache.set(lock_key, True, timeout=7200)

        try:
            from core.models import QuickLessonMatch, PointBalance, PointTransaction

            match = QuickLessonMatch.objects.select_related(
                'request__student__user',
                'tutor__user',
            ).get(id=self.match_id)

            # 1分未満の会話はポイント変動なし
            if match.started_at and match.end_at:
                duration = (match.end_at - match.started_at).total_seconds()
                if duration < 60:
                    print(f"[points] match {self.match_id}: duration {duration:.0f}s < 60s, skipping")
                    return

            student_user = match.request.student.user
            tutor_user   = match.tutor.user

            # 生徒: -1pt（Gold会員・残高不足は免除）
            from core.models import GoldMembership
            from django.utils import timezone as _tz
            student_is_gold = False
            try:
                gm = GoldMembership.objects.get(user=student_user)
                student_is_gold = gm.expires_at > _tz.now()
            except GoldMembership.DoesNotExist:
                pass

            if not student_is_gold:
                s_bal, _ = PointBalance.objects.get_or_create(user=student_user)
                if s_bal.student_balance >= 1:
                    s_bal.student_balance -= 1
                    s_bal.save()
                    PointTransaction.objects.create(
                        user=student_user,
                        amount=-1,
                        transaction_type=PointTransaction.TYPE_LESSON_TAKEN,
                        reference_id=int(self.match_id),
                    )

            # 講師: +1pt を講師ポイントに加算
            t_bal, _ = PointBalance.objects.get_or_create(user=tutor_user)
            t_bal.teacher_balance += 1
            t_bal.save()
            PointTransaction.objects.create(
                user=tutor_user,
                amount=1,
                transaction_type=PointTransaction.TYPE_LESSON_TAUGHT,
                reference_id=int(self.match_id),
            )

        except Exception as e:
            # ポイント処理失敗してもレッスン自体は止めない
            print(f"[points] Error processing match {self.match_id}: {e}")
