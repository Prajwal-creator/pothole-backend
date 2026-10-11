
from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    is_online = serializers.ReadOnlyField()

    class Meta:
        model = Device
        fields = [
            'device_id',
            'name',
            'is_active',
            'created_at',
            'last_seen',
            'is_online',
            'battery_percent',
            'wifi_rssi',
            'gps_connected',
            'mpu6050_connected',
            'camera_connected',
        ]

        read_only_fields = [
            'created_at',
            'last_seen',
            'is_online',
            'battery_percent',
            'wifi_rssi',
            'gps_connected',
            'mpu6050_connected',
            'camera_connected',
        ]
