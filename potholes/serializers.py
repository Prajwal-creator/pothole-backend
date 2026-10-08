from rest_framework import serializers
from .models import Pothole


class PotholeSerializer(serializers.ModelSerializer):

    device_id = serializers.CharField(
        source="device.device_id",
        read_only=True
    )

    device_name = serializers.CharField(
        source="device.name",
        read_only=True
    )

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Pothole

        fields = [
            "pothole_id",

            "device_id",
            "device_name",

            "image",
            "image_url",

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
        ]

        read_only_fields = [
            "pothole_id",
            "device_id",
            "device_name",
            "image_url",
            "detected_at",
        ]

    def get_image_url(self, obj):

        request = self.context.get("request")

        if obj.image and request:
            return request.build_absolute_uri(
                obj.image.url
            )

        return None