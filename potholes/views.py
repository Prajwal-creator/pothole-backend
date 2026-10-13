from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from devices.models import Device
from .models import Pothole
from .serializers import PotholeSerializer
from .utils import rgb565_to_jpeg
from rest_framework.parsers import MultiPartParser, FormParser
import hashlib
import hmac


class PotholeDetectView(APIView):

    parser_classes = [
    MultiPartParser,
    FormParser
   ]

    def post(self, request):

        # ==================================================
        # DEVICE AUTHENTICATION
        # ==================================================

        device_id = request.headers.get(
            "Device-ID"
        )

        device_token = request.headers.get(
            "Device-Token"
        )

        if not device_id:
            return Response(
                {
                    "success": False,
                    "error": "Device-ID header is required"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not device_token:
            return Response(
                {
                    "success": False,
                    "error": "Device-Token header is required"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ==================================================
        # FIND DEVICE
        # ==================================================

        try:

            device = Device.objects.get(
                device_id=device_id
            )

        except Device.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "error": "Unknown device"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ==================================================
        # CHECK DEVICE ACTIVE
        # ==================================================

        if not device.is_active:

            return Response(
                {
                    "success": False,
                    "error": "Device is inactive"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # ==================================================
        # CHECK TOKEN
        # ==================================================

        provided_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(provided_hash,device.device_token_hash):
            return Response(
                {
                   "success": False,
                   "error": "Invalid device token"
                },
                     status=status.HTTP_401_UNAUTHORIZED
            )

    

        # ==================================================
        # GET IMAGE
        # ==================================================

        image_file = request.FILES.get(
            "image"
        )

        if not image_file:

            return Response(
                {
                    "success": False,
                    "error": "RGB565 image is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # GET WIDTH / HEIGHT
        # ==================================================

        try:

            width = int(
                request.data.get(
                    "width",
                    240
                )
            )

            height = int(
                request.data.get(
                    "height",
                    240
                )
            )

        except ValueError:

            return Response(
                {
                    "success": False,
                    "error": "Invalid width or height"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # READ RGB565 DATA
        # ==================================================

        try:

            raw_image = image_file.read()

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": f"Could not read image: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # CONVERT RGB565 -> JPEG
        # ==================================================

        try:

           jpeg_file = rgb565_to_jpeg(
           raw_data=raw_image,
           width=int(width),
           height=int(height),
           quality=85,
           byte_order="big",
           )

           jpeg_file.seek(0)
           

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # READ GPS
        # ==================================================

        try:

            latitude = float(
                request.data.get(
                    "latitude"
                )
            )

            longitude = float(
                request.data.get(
                    "longitude"
                )
            )

            speed = float(
                request.data.get(
                    "speed",
                    0
                )
            )

            accuracy = float(
                request.data.get(
                    "accuracy",
                    0
                )
            )

            satellites = int(
                request.data.get(
                    "satellites",
                    0
                )
            )

        except (TypeError, ValueError):

            return Response(
                {
                    "success": False,
                    "error": "Invalid GPS data"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # READ MPU6050
        # ==================================================

        try:

            ax = float(
                request.data.get(
                    "ax",
                    0
                )
            )

            ay = float(
                request.data.get(
                    "ay",
                    0
                )
            )

            az = float(
                request.data.get(
                    "az",
                    0
                )
            )

        except (TypeError, ValueError):

            return Response(
                {
                    "success": False,
                    "error": "Invalid sensor data"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # POTHOLE INFORMATION
        # ==================================================

        severity = request.data.get(
            "severity",
            "Medium"
        )

        confidence = float(
            request.data.get(
                "confidence",
                0
            )
        )

        # ==================================================
        # SAVE POTHOLE
        # ==================================================

        try:

            with transaction.atomic():

                pothole = Pothole(

                    device=device,

                    latitude=latitude,
                    longitude=longitude,

                    speed=speed,
                    accuracy=accuracy,
                    satellites=satellites,

                    ax=ax,
                    ay=ay,
                    az=az,

                    severity=severity,
                    confidence=confidence,

                    status="Pending"
                )

                # Temporary save to generate ID
                pothole.save()

                # ==================================================
                # SAVE JPEG
                # ==================================================

                filename = (
                    f"{pothole.pothole_id}.jpg"
                )

                pothole.image.save(
                    filename,
                    jpeg_file,
                    save=True
                )

                # ==================================================
                # UPDATE DEVICE
                # ==================================================

                device.last_seen = timezone.now()

                device.save(
                    update_fields=[
                        "last_seen"
                    ]
                )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "error": f"Database error: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ==================================================
        # RESPONSE
        # ==================================================

        serializer = PotholeSerializer(
            pothole,
            context={
                "request": request
            }
        )

        return Response(
            {
                "success": True,

                "message": "Pothole detected successfully",

                "pothole": serializer.data
            },
            status=status.HTTP_201_CREATED
        )