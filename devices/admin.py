from django.contrib import admin
from .models import Device

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_id',
        'name',
        'is_active',
        'online_status',
        'created_at',
        'last_seen',
        'battery_percent',
        'wifi_rssi',
        'gps_connected',
        'mpu6050_connected',
       'camera_connected'
    )

    search_fields = (
        'device_id',
        'name',
    )

    list_filter = (
        'is_active',
    )

    readonly_fields = ("online_status",)

    @admin.display(description="Online Status", boolean=True)
    def online_status(self, obj):


         return obj.is_online