from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Device
        fields = [
            'device_id',
            'name',
            'is_active',
            'created_at',
            'last_seen',
        ]

        read_only_fields = [
            'created_at',
            'last_seen',
        ]