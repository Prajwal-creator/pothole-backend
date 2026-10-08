from django.db import models



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

    def __str__(self):
        return f"{self.name} ({self.device_id})"

