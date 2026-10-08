from django.contrib import admin
from .models import Telemetry


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):

    list_display = (
        'device',
        'latitude',
        'longitude',
        'speed',
        'satellites',
        'created_at',
    )

    list_filter = (
        'device',
        'created_at',
    )

    search_fields = (
        'device__device_id',
    )

    ordering = (
        '-created_at',
    )
