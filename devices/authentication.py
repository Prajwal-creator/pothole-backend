import hashlib
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Device


class DeviceAuthentication(BaseAuthentication):

    def authenticate(self, request):

        token = request.headers.get('X-Device-Token')

        if not token:
            return None

        token = token.strip()

        if not token:
            raise AuthenticationFailed(
                'Device token is required.'
            )

        token_hash = hashlib.sha256(
            token.encode()
        ).hexdigest()

        device = Device.objects.filter(
            device_token_hash=token_hash
        ).first()

        if device is None:
            raise AuthenticationFailed(
                'Invalid device token.'
            )

        if not device.is_active:
            raise AuthenticationFailed(
                'Device is suspended.'
            )

        return (
            device,
            None
        )