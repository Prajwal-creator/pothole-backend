from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from devices.authentication import DeviceAuthentication
from devices.models import Device
from .models import Telemetry


class DeviceTelemetryView(APIView):

    authentication_classes = [
        DeviceAuthentication
    ]

    def post(self, request, device_id):

        # DeviceAuthentication returns the Device
        device = request.user

        # Make sure URL device_id matches
        # authenticated device
        if device.device_id != device_id:

            return Response(
                {
                    "message": "Device authentication mismatch."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data

        gps = data.get("gps", {})
        sensor = data.get("sensor", {})

        # -------------------------
        # Validate GPS
        # -------------------------

        latitude = gps.get("latitude")
        longitude = gps.get("longitude")

        if latitude is None:
            return Response(
                {
                    "message": "GPS latitude is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if longitude is None:
            return Response(
                {
                    "message": "GPS longitude is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------
        # Validate GPS range
        # -------------------------

        try:
            latitude = float(latitude)
            longitude = float(longitude)

        except (TypeError, ValueError):

            return Response(
                {
                    "message": "Invalid GPS coordinates."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not -90 <= latitude <= 90:

            return Response(
                {
                    "message": "Invalid latitude."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not -180 <= longitude <= 180:

            return Response(
                {
                    "message": "Invalid longitude."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------
        # Optional values
        # -------------------------

        speed = gps.get("speed")
        accuracy = gps.get("accuracy")
        satellites = gps.get("satellites")

        ax = sensor.get("ax")
        ay = sensor.get("ay")
        az = sensor.get("az")

        # Convert numbers safely

        try:
            if speed is not None:
                speed = float(speed)

            if accuracy is not None:
                accuracy = float(accuracy)

            if satellites is not None:
                satellites = int(satellites)

            if ax is not None:
                ax = float(ax)

            if ay is not None:
                ay = float(ay)

            if az is not None:
                az = float(az)

        except (TypeError, ValueError):

            return Response(
                {
                    "message": "Invalid telemetry values."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------
        # Save telemetry
        # -------------------------

        telemetry = Telemetry.objects.create(

            device=device,

            latitude=latitude,
            longitude=longitude,

            speed=speed,
            accuracy=accuracy,
            satellites=satellites,

            ax=ax,
            ay=ay,
            az=az,
        )

        # -------------------------
        # Update last_seen
        # -------------------------

        device.last_seen = timezone.now()

        device.save(
            update_fields=['last_seen']
        )

        return Response(
            {
                "message": "Telemetry received successfully.",
                "telemetry_id": telemetry.id,
                "device_id": device.device_id,
                "received_at": telemetry.created_at,
            },
            status=status.HTTP_201_CREATED
        )