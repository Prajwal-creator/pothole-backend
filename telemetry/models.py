from django.db import models
from devices.models import Device


class Telemetry(models.Model):

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='telemetry'
    )

    # GPS
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(
        null=True,
        blank=True
    )
    accuracy = models.FloatField(
        null=True,
        blank=True
    )
    satellites = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # MPU6050
    ax = models.FloatField(
        null=True,
        blank=True
    )
    ay = models.FloatField(
        null=True,
        blank=True
    )
    az = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    last_seen = models.DateTimeField(
    null=True,
    blank=True
    )

    def __str__(self):
        return f"{self.device.device_id} - {self.created_at}"
