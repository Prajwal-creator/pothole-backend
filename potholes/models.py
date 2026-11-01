from django.db import models
from devices.models import Device


class Pothole(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Verified", "Verified"),
        ("Rejected", "Rejected"),
        ("Repaired", "Repaired"),
    ]

    SEVERITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Critical", "Critical"),
    ]

    pothole_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="potholes"
    )

    image = models.ImageField(
        upload_to="potholes/%Y/%m/%d/"
    )

    latitude = models.FloatField()
    longitude = models.FloatField()

    speed = models.FloatField(
        default=0
    )

    accuracy = models.FloatField(
        default=0
    )

    satellites = models.IntegerField(
        default=0
    )

    ax = models.FloatField(
        default=0
    )

    ay = models.FloatField(
        default=0
    )

    az = models.FloatField(
        default=0
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="Medium"
    )

    confidence = models.FloatField(
        default=0
    )

    is_pothole = models.BooleanField(default=False)

    label = models.CharField(
        max_length=30,
        default="no_pothole"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    detected_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        ordering = ["-detected_at"]

    def save(self, *args, **kwargs):

        if not self.pothole_id:
            last = Pothole.objects.order_by("-id").first()

            if last:
                number = last.id + 1000
            else:
                number = 1000

            self.pothole_id = f"PH-{number}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.pothole_id