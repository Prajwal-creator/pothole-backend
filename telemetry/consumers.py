import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from telemetry.models import Telemetry


class DeviceTelemetryConsumer(AsyncWebsocketConsumer):

    OFFLINE_AFTER_SECONDS = 15

    async def connect(self):
        self.device_id = self.scope["url_route"]["kwargs"]["device_id"]
        self.device = self.scope.get("device")

        # Device authentication
        if self.device is None:
            print("Device authentication failed")
            await self.close(code=4001)
            return

        if self.device.device_id != self.device_id:
            await self.close(code=4001)
            return

        # Device active check
        if not self.device.is_active:
            print(f"Device inactive: {self.device_id}")
            await self.close(code=4003)
            return

        self.device_group = f"device_{self.device_id}"
        self.telemetry_group = "telemetry_all"

        await self.channel_layer.group_add(
            self.device_group, self.channel_name
        )
        await self.channel_layer.group_add(
            self.telemetry_group, self.channel_name
        )

        await self.accept()

        print(f"Device WebSocket connected: {self.device_id}")

        await self.send(text_data=json.dumps({
            "type": "connection",
            "status": "connected",
            "device_id": self.device_id,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "device_group"):
            await self.channel_layer.group_discard(
                self.device_group, self.channel_name
            )

        if hasattr(self, "telemetry_group"):
            await self.channel_layer.group_discard(
                self.telemetry_group, self.channel_name
            )

        print(
            f"Device WebSocket disconnected: "
            f"{getattr(self, 'device_id', 'unknown')}; "
            f"close_code={close_code}"
        )

        # Do not immediately mark offline here.
        # A device may reconnect; last_seen timeout determines status.

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            print("\n========== ESP32 DATA RECEIVED ==========")
            print(f"Device ID: {self.device_id}")
            print("Full payload:")
            print(json.dumps(data, indent=2))
            print("==========================================\n")
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

        # Never trust a device_id supplied in the payload.
        # Use the device authenticated for this WebSocket.
        if not self.device.is_active:
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

        # Update last_seen and metrics for every valid heartbeat.
        # Sensor health must be reported explicitly by the ESP32.
        try:
            device_status = await self.update_device_status(data)

        except Exception as exc:
            print("Device status update failed:", str(exc))
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Device status update failed",
            }))
            return

        await self.channel_layer.group_send(
            self.telemetry_group,
            {
                "type": "device_status_update",
                "device_id": self.device_id,
                "status": (
                    "online" if device_status["is_online"] else "offline"
                ),
                "last_seen": device_status["last_seen"],
                "battery_percent": device_status["battery_percent"],
                "wifi_rssi": device_status["wifi_rssi"],
                "gps_connected": device_status["gps_connected"],
                "mpu6050_connected": device_status["mpu6050_connected"],
                "camera_connected": device_status["camera_connected"],
            }
        )

        # A heartbeat without GPS coordinates still counts as a heartbeat.
        # Save a Telemetry row only when GPS coordinates are supplied.
        latitude = gps.get("latitude")
        longitude = gps.get("longitude")

        has_coordinates = (
            latitude is not None and longitude is not None
        )

        telemetry_id = None

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
                self.telemetry_group,
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
                    "battery_percent": device_status["battery_percent"],
                    "wifi_rssi": device_status["wifi_rssi"],
                }
            )

        await self.send(text_data=json.dumps({
            "type": "ack",
            "status": "received",
            "database": "saved" if telemetry_id is not None else "heartbeat",
            "telemetry_id": telemetry_id,
            "device_id": self.device_id,
        }))

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
    def update_device_status(self, data):
        from django.utils import timezone

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

        self.device.__class__.objects.filter(
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
