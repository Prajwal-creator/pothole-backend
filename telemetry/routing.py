from django.urls import re_path

from .consumers import DeviceTelemetryConsumer
from .middleware import DeviceAuthMiddleware


websocket_urlpatterns = [

    re_path(
        r"ws/devices/(?P<device_id>[^/]+)/telemetry/$",

        DeviceAuthMiddleware(
            DeviceTelemetryConsumer.as_asgi()
        ),

    ),

]