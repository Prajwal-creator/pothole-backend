from rest_framework import serializers
from .models import Telemetry


class TelemetrySerializer(serializers.ModelSerializer):

    class Meta:
        model = Telemetry

        fields = [
            'id',
            'device',
            'latitude',
            'longitude',
            'speed',
            'accuracy',
            'satellites',
            'ax',
            'ay',
            'az',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'device',
            'created_at',
        ]