
import hashlib
import hmac
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import Device


class DeviceAuthMiddleware:
    """
    ESP32 authentication.

    Supports:
      Authorization: Token <device_token>
    or:
      ?token=<device_token>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["device"] = None

        try:
            device_id = scope["url_route"]["kwargs"]["device_id"]
        except (KeyError, TypeError):
            await self.close_connection(send, 4001)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        raw_token = None
        print(auth_header)

        if auth_header:
            try:
                auth_header = auth_header.decode("utf-8")
            except UnicodeDecodeError:
                await self.close_connection(send, 4001)
                return

            if not auth_header.startswith("Token "):
                await self.close_connection(send, 4001)
                return
            
            raw_token = auth_header[6:].strip()

        else:
            query_string = scope.get(
                "query_string", b""
            ).decode("utf-8", errors="replace")

            params = parse_qs(query_string)
            raw_token = params.get("token", [None])[0]

        if not raw_token:
            await self.close_connection(send, 4001)
            return

        device = await self.authenticate_device(
            device_id, raw_token
        )

        if device is None:
            await self.close_connection(send, 4003)
            return

        scope["device"] = device
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def authenticate_device(self, device_id, raw_token):
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return None

        if not device.is_active:
            return None

        if not device.device_token_hash:
            return None

        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        if not hmac.compare_digest(
            token_hash, device.device_token_hash
        ):
            return None

        return device

    async def close_connection(self, send, code):
        await send({
            "type": "websocket.close",
            "code": code,
        })


class DashboardJWTAuthMiddleware:
    """
    React dashboard authentication using a Django user JWT.

    URL:
      /ws/dashboard/devices/<device_id>/telemetry/?token=<user_jwt>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()

        query_string = scope.get(
            "query_string", b""
        ).decode("utf-8", errors="replace")
        print("Path:", scope.get("path"))
        print("Query parameters present:", bool(query_string))

        params = parse_qs(query_string)
        raw_token = params.get("token", [None])[0]

        if not raw_token:
            await self.close_connection(send, 4001)
            return

        try:
            user = await self.get_user(raw_token)
        except Exception as exc:
            # Never log the actual JWT.
            print(
                "Dashboard JWT rejected:",
                type(exc).__name__,
            )
            await self.close_connection(send, 4001)
            return

        if not user or not user.is_active:
            await self.close_connection(send, 4003)
            return

        scope["user"] = user

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, raw_token):
        validated_token = JWTAuthentication().get_validated_token(
            raw_token
        )

        return JWTAuthentication().get_user(validated_token)

    async def close_connection(self, send, code):
        await send({
            "type": "websocket.close",
            "code": code,
        })
