
from django.db import models
from django.utils import timezone


class Device(models.Model):
    device_id = models.CharField(
        max_length=100,
        unique=True
    )

    name = models.CharField(
        max_length=150
    )

    is_active = models.BooleanField(
        default=True
    )

    device_token_hash = models.CharField(
        max_length=128
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    # Live device metrics
    battery_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    wifi_rssi = models.IntegerField(
        null=True,
        blank=True
    )

    # Individual sensor health
    gps_connected = models.BooleanField(default=False)
    mpu6050_connected = models.BooleanField(default=False)
    camera_connected = models.BooleanField(default=False)

    @property
    def is_online(self):
        if not self.is_active or not self.last_seen:
            return False

        elapsed = (
            timezone.now() - self.last_seen
        ).total_seconds()

        return elapsed <= 15

    def __str__(self):
        return f"{self.name} ({self.device_id})"
