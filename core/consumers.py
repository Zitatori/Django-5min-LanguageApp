import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

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
                "message": {
                    "type": "peer_left",
                },
                "sender_channel_name": "",
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        # joinシグナルを受け取ったらカウントして判定
        if data.get("type") == "join":
            count_key = f"room_count_{self.match_id}"
            count = cache.get(count_key, 0) + 1
            cache.set(count_key, count, timeout=3600)

            if count >= 2:
                # 2人揃ったのでタイマー開始シグナルを全員に送る
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_signal",
                        "message": {
                            "type": "timer_start",
                            "seconds": 300,
                        },
                        "sender_channel_name": "",  # 全員に届ける
                    }
                )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "send_signal",
                "message": data,
                "sender_channel_name": self.channel_name,
            }
        )

    async def send_signal(self, event):
        # sender_channel_nameが空なら全員に届ける（timer_start用）
        if event["sender_channel_name"] and event["sender_channel_name"] == self.channel_name:
            return

        await self.send(text_data=json.dumps(event["message"]))