from django.contrib import admin
from .models import Device

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_id',
        'name',
        'is_active',
        'created_at',
        'last_seen',
    )

    search_fields = (
        'device_id',
        'name',
    )

    list_filter = (
        'is_active',
    )

# Register your models here.
