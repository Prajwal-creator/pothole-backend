import hashlib
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from devices.models import Device


class DeviceAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        print("================================")
        print("DEVICE WEBSOCKET AUTH")
        print("PATH:", scope.get("path"))
        print("URL ROUTE:", scope.get("url_route"))
        print("================================")

        scope["device"] = None

        # 1. Get device ID from URL routing
        try:
            device_id = scope["url_route"]["kwargs"]["device_id"]
        except (KeyError, TypeError):
            print("ERROR: device_id not found")
            return await self.close_connection(send, 4001)

        # 2. Try Authorization header first (ESP32/header clients)
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")

        raw_token = None
        auth_method = None

        if auth_header:
            try:
                auth_header = auth_header.decode("utf-8")
            except UnicodeDecodeError:
                print("ERROR: Invalid authorization encoding")
                return await self.close_connection(send, 4001)

            if not auth_header.startswith("Token "):
                print("ERROR: Expected Authorization: Token <token>")
                return await self.close_connection(send, 4001)

            raw_token = auth_header[6:].strip()
            auth_method = "Authorization header"

        else:
            # 3. If header is absent, try React's URL query parameter
            query_string = scope.get("query_string", b"").decode(
                "utf-8", errors="replace"
            )
            params = parse_qs(query_string)
            raw_token = params.get("token", [None])[0]
            auth_method = "URL query parameter"

        # 4. Reject missing or empty token
        if not raw_token:
            print("ERROR: No valid token supplied")
            return await self.close_connection(send, 4001)

        print("Authentication method:", auth_method)
        print("Authenticating device:", device_id)

        # 5. Validate the same token using your existing SHA-256 logic
        device = await self.authenticate_device(device_id, raw_token)

        if device is None:
            print("ERROR: Device authentication failed")
            return await self.close_connection(send, 4003)

        # 6. Authentication successful
        scope["device"] = device

        print("SUCCESS: Device authenticated:", device.device_id)

        # 7. Continue to the WebSocket consumer
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def authenticate_device(self, device_id, raw_token):

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            print("Device does not exist:", device_id)
            return None

        if not device.is_active:
            print("Device is inactive:", device_id)
            return None

        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        if token_hash != device.device_token_hash:
            print("Token hash mismatch")
            return None

        return device

    async def close_connection(self, send, code):
        await send({
            "type": "websocket.close",
            "code": code,
        })