
# potholes/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_id = self.scope["url_route"]["kwargs"]["device_id"]
        self.group_name = f"camera_{self.device_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

        print(f"Camera WebSocket connected: {self.device_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    async def capture_request(self, event):
        await self.send(text_data=json.dumps({
            "type": "capture_request",
            "request_id": event["request_id"],
        }))
