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

        # 退室時にカウントを減らす
        count_key = f"room_count_{self.match_id}"
        count = cache.get(count_key, 0)
        count = max(0, count - 1)
        cache.set(count_key, count, timeout=3600)

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
            count_key = f"room_count_{self.match_id}"
            try:
                count = cache.incr(count_key)   # atomic on Redis/Memcached
            except ValueError:
                cache.set(count_key, 1, timeout=3600)
                count = 1
            print(f"[ws] match={self.match_id} join count={count} ch={self.channel_name[:8]}")

            if count >= 2:
                # 2人揃った → タイマー開始
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_signal",
                        "message": {"type": "timer_start", "seconds": 300},
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
                if s_bal.balance >= 1:
                    s_bal.balance -= 1
                    s_bal.save()
                    PointTransaction.objects.create(
                        user=student_user,
                        amount=-1,
                        transaction_type=PointTransaction.TYPE_LESSON_TAKEN,
                        reference_id=int(self.match_id),
                    )

            # 講師: +1pt（引き出し可能額にも加算）
            t_bal, _ = PointBalance.objects.get_or_create(user=tutor_user)
            t_bal.balance         += 1
            t_bal.earned_balance  += 1
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