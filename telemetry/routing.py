from django.urls import re_path

from telemetry.consumers import (
    DeviceTelemetryConsumer,
    DashboardTelemetryConsumer,
)
from telemetry.middleware import (
    DeviceAuthMiddleware,
    DashboardJWTAuthMiddleware,
)

from potholes.consumers import CameraConsumer

websocket_urlpatterns = [
    # ESP32 uploads telemetry using the device token.
    re_path(
        r"^ws/devices/(?P<device_id>[^/]+)/telemetry/$",
        DeviceAuthMiddleware(
            DeviceTelemetryConsumer.as_asgi()
        ),
    ),

    # React receives live data using the user's JWT.
    re_path(
        r"^ws/dashboard/devices/(?P<device_id>[^/]+)/telemetry/$",
        DashboardJWTAuthMiddleware(
            DashboardTelemetryConsumer.as_asgi()
        ),
    ),

    re_path(
        r"^ws/camera/(?P<device_id>[^/]+)/$",
        CameraConsumer.as_asgi(),
    ),
]
