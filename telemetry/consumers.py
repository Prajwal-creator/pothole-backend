
import hashlib
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from devices.models import Device
from telemetry.models import Telemetry


def dashboard_group_name(device_id):
    """
    Use a predictable, short, valid Channels group name.
    This also supports long device IDs.
    """
    digest = hashlib.sha256(
        device_id.encode("utf-8")
    ).hexdigest()[:40]

    return f"dashboard_{digest}"


class DeviceTelemetryConsumer(AsyncWebsocketConsumer):
    """
    ESP32 producer connection.
    Authentication is handled by DeviceAuthMiddleware.
    """

    async def connect(self):
        self.device_id = self.scope[
            "url_route"
        ]["kwargs"]["device_id"]

        self.device = self.scope.get("device")

        if self.device is None:
            await self.close(code=4001)
            return

        if self.device.device_id != self.device_id:
            await self.close(code=4001)
            return

        if not self.device.is_active:
            await self.close(code=4003)
            return

        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection",
            "status": "connected",
            "device_id": self.device_id,
        }))

        print("ESP32 connected:", self.device_id)

    async def disconnect(self, close_code):
        print(
            "ESP32 disconnected:",
            self.device_id,
            "code:",
            close_code,
        )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:

            return

        try:

            data = json.loads(text_data)
            print("\n========== ESP32 PAYLOAD ==========")
            print(json.dumps(data, indent=2))
            print("GPS:", data.get("gps"))
            print("SENSOR:", data.get("sensor"))
            print("GPS CONNECTED:", data.get("gps_connected"))
            print("MPU6050 CONNECTED:", data.get("mpu6050_connected"))
            print("BATTERY:", data.get("battery_percent"))
            print("==================================\n")
        except (json.JSONDecodeError, TypeError):
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON",
            }))
            return

        if not isinstance(data, dict):
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "JSON message must be an object",
            }))
            return

        if not await self.is_device_active():
            await self.close(code=4003)
            return

        gps = data.get("gps") or {}
        sensor = data.get("sensor") or {}

        if not isinstance(gps, dict) or not isinstance(sensor, dict):
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "gps and sensor must be JSON objects",
            }))
            return

        try:
            device_status = await self.update_device_status(data)
        except Exception as exc:
            print("Device status update failed:", str(exc))
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Device status update failed",
            }))
            return

        # Publish status only to dashboards subscribed to this device.
        await self.channel_layer.group_send(
            dashboard_group_name(self.device_id),
            {
                "type": "device_status_update",
                "device_id": self.device_id,
                "status": (
                    "online"
                    if device_status["is_online"]
                    else "offline"
                ),
                "last_seen": device_status["last_seen"],
                "battery_percent": device_status["battery_percent"],
                "wifi_rssi": device_status["wifi_rssi"],
                "gps_connected": device_status["gps_connected"],
                "mpu6050_connected": device_status[
                    "mpu6050_connected"
                ],
                "camera_connected": device_status[
                    "camera_connected"
                ],
            },
        )

        latitude = gps.get("latitude")
        longitude = gps.get("longitude")

        has_coordinates = (
            latitude is not None
            and longitude is not None
        )

        telemetry_id = None

        # Save a telemetry row only when GPS coordinates are provided.
        if has_coordinates:
            try:
                telemetry_id = await self.save_telemetry(
                    latitude=latitude,
                    longitude=longitude,
                    speed=gps.get("speed"),
                    accuracy=gps.get("accuracy"),
                    satellites=gps.get("satellites"),
                    ax=sensor.get("ax"),
                    ay=sensor.get("ay"),
                    az=sensor.get("az"),
                )
            except Exception as exc:
                print("Telemetry save failed:", str(exc))
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Telemetry save failed",
                }))
                return

            await self.channel_layer.group_send(
                dashboard_group_name(self.device_id),
                {
                    "type": "telemetry_update",
                    "device_id": self.device_id,
                    "telemetry_id": telemetry_id,
                    "gps": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "speed": gps.get("speed"),
                        "accuracy": gps.get("accuracy"),
                        "satellites": gps.get("satellites"),
                    },
                    "sensor": {
                        "ax": sensor.get("ax"),
                        "ay": sensor.get("ay"),
                        "az": sensor.get("az"),
                    },
                    "battery_percent": device_status[
                        "battery_percent"
                    ],
                    "wifi_rssi": device_status["wifi_rssi"],
                },
            )

        await self.send(text_data=json.dumps({
            "type": "ack",
            "status": "received",
            "database": (
                "saved" if telemetry_id is not None
                else "heartbeat"
            ),
            "telemetry_id": telemetry_id,
            "device_id": self.device_id,
        }))

    async def telemetry_update(self, event):
        # The ESP32 producer does not need dashboard messages.
        pass

    async def device_status_update(self, event):
        # The ESP32 producer does not need dashboard messages.
        pass

    @database_sync_to_async
    def is_device_active(self):
        return Device.objects.filter(
            pk=self.device.pk,
            is_active=True,
        ).exists()

    @database_sync_to_async
    def update_device_status(self, data):
        updates = {"last_seen": timezone.now()}

        battery = data.get("battery_percent")
        if (
            isinstance(battery, int)
            and not isinstance(battery, bool)
            and 0 <= battery <= 100
        ):
            updates["battery_percent"] = battery

        rssi = data.get("wifi_rssi")
        if (
            isinstance(rssi, int)
            and not isinstance(rssi, bool)
            and -150 <= rssi <= 0
        ):
            updates["wifi_rssi"] = rssi

        for field in (
            "gps_connected",
            "mpu6050_connected",
            "camera_connected",
        ):
            value = data.get(field)
            if isinstance(value, bool):
                updates[field] = value

        Device.objects.filter(
            pk=self.device.pk
        ).update(**updates)

        self.device.refresh_from_db()

        return {
            "is_online": self.device.is_online,
            "last_seen": (
                self.device.last_seen.isoformat()
                if self.device.last_seen else None
            ),
            "battery_percent": self.device.battery_percent,
            "wifi_rssi": self.device.wifi_rssi,
            "gps_connected": self.device.gps_connected,
            "mpu6050_connected": self.device.mpu6050_connected,
            "camera_connected": self.device.camera_connected,
        }

    @database_sync_to_async
    def save_telemetry(
        self,
        latitude,
        longitude,
        speed,
        accuracy,
        satellites,
        ax,
        ay,
        az,
    ):
        telemetry = Telemetry.objects.create(
            device=self.device,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            accuracy=accuracy,
            satellites=satellites,
            ax=ax,
            ay=ay,
            az=az,
        )

        return telemetry.id


class DashboardTelemetryConsumer(AsyncWebsocketConsumer):
    """
    React dashboard connection.
    Uses the authenticated Django user, not a device token.
    This consumer is read-only.
    """

    async def connect(self):
        self.device_id = self.scope[
            "url_route"
        ]["kwargs"]["device_id"]

        self.user = self.scope.get("user")

        if (
            not self.user
            or not self.user.is_authenticated
            or not self.user.is_active
        ):
            await self.close(code=4001)
            return

        self.device = await self.get_device(self.device_id)

        if self.device is None or not self.device.is_active:
            await self.close(code=4003)
            return

        # IMPORTANT:
        # If users have device assignments/roles, verify authorization
        # here before allowing this connection.

        self.dashboard_group = dashboard_group_name(
            self.device_id
        )

        await self.channel_layer.group_add(
            self.dashboard_group,
            self.channel_name,
        )

        await self.accept()

        # Send current device status immediately.
        await self.send(text_data=json.dumps({
            "type": "connection",
            "status": "connected",
            "device_id": self.device.device_id,
        }))

        await self.send(text_data=json.dumps({
            "type": "device_status",
            "device_id": self.device.device_id,
            "status": (
                "online" if self.device.is_online else "offline"
            ),
            "last_seen": (
                self.device.last_seen.isoformat()
                if self.device.last_seen else None
            ),
            "battery_percent": self.device.battery_percent,
            "wifi_rssi": self.device.wifi_rssi,
            "gps_connected": self.device.gps_connected,
            "mpu6050_connected": self.device.mpu6050_connected,
            "camera_connected": self.device.camera_connected,
        }))

        print(
            "Dashboard connected:",
            self.user.pk,
            self.device_id,
        )

    async def disconnect(self, close_code):
        if hasattr(self, "dashboard_group"):
            await self.channel_layer.group_discard(
                self.dashboard_group,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        # Dashboard clients are not allowed to send telemetry.
        await self.close(code=4003)

    async def telemetry_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "telemetry",
            "device_id": event["device_id"],
            "telemetry_id": event.get("telemetry_id"),
            "gps": event["gps"],
            "sensor": event["sensor"],
            "battery_percent": event.get("battery_percent"),
            "wifi_rssi": event.get("wifi_rssi"),
        }))

    async def device_status_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "device_status",
            "device_id": event["device_id"],
            "status": event["status"],
            "last_seen": event.get("last_seen"),
            "battery_percent": event.get("battery_percent"),
            "wifi_rssi": event.get("wifi_rssi"),
            "gps_connected": event.get("gps_connected"),
            "mpu6050_connected": event.get("mpu6050_connected"),
            "camera_connected": event.get("camera_connected"),
        }))

    @database_sync_to_async
    def get_device(self, device_id):
        return Device.objects.filter(
            device_id=device_id
        ).first()
