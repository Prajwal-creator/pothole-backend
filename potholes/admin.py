from django.contrib import admin
from .models import Pothole


@admin.register(Pothole)
class PotholeAdmin(admin.ModelAdmin):

    # Columns shown in the pothole list
    list_display = (
        "pothole_id",
        "device",
        "image_preview",
        "latitude",
        "longitude",
        "speed",
        "accuracy",
        "satellites",
        "ax",
        "ay",
        "az",
        "severity",
        "confidence",
        "status",
        "detected_at",
    )

    # Filters on the right side
    list_filter = (
        "device",
        "severity",
        "status",
        "detected_at",
    )

    # Search box
    search_fields = (
        "pothole_id",
        "device__device_id",
        "device__name",
        "latitude",
        "longitude",
    )

    # Default ordering
    ordering = (
        "-detected_at",
    )

    # Fields shown when editing a pothole
    readonly_fields = (
        "pothole_id",
        "detected_at",
        "image_preview",
    )

    # Organize the edit page
    fieldsets = (
        (
            "Pothole Information",
            {
                "fields": (
                    "pothole_id",
                    "device",
                    "image",
                    "image_preview",
                    "severity",
                    "confidence",
                    "status",
                )
            }
        ),

        (
            "GPS Information",
            {
                "fields": (
                    "latitude",
                    "longitude",
                    "speed",
                    "accuracy",
                    "satellites",
                )
            }
        ),

        (
            "MPU6050 Sensor",
            {
                "fields": (
                    "ax",
                    "ay",
                    "az",
                )
            }
        ),

        (
            "Detection Time",
            {
                "fields": (
                    "detected_at",
                )
            }
        ),
    )

    # Image preview
    @admin.display(
        description="Image"
    )
    def image_preview(self, obj):

        if obj.image:

            from django.utils.html import format_html

            return format_html(
                '<img src="{}" width="120" height="120" '
                'style="object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )

        return "No Image"
