from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from devices.models import Device
from .models import Pothole
from .yolo_detector import detect_pothole
from .serializers import PotholeSerializer
from .utils import rgb565_to_jpeg
from rest_framework.parsers import MultiPartParser, FormParser
import hashlib
import hmac
import uuid
from django.core.cache import cache
from django.http import HttpResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes,
)
from rest_framework.permissions import IsAuthenticated
import tempfile

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
           print(f"the width {width}")
           print(f"the height is {height}")
           jpeg_file = rgb565_to_jpeg(
           raw_data=raw_image,
           width=int(width),
           height=int(height),
           quality=85,
           byte_order="big",
           )
           with tempfile.NamedTemporaryFile(
               suffix=".jpg",
               delete=False
           ) as temp_file:
               temp_file.write(jpeg_file.read())
               temp_image_path = temp_file.name

           prediction = detect_pothole(
               image_path=temp_image_path,
               threshold=0.10
           )

           print("Pothole detected:", prediction["is_pothole"])
           print("Label:", prediction["label"])
           print("Confidence:", prediction["confidence"])
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
                from django.core.files.base import ContentFile
                filename = f"{pothole.pothole_id}.jpg"
                if prediction["is_pothole"]:
                    annotated_file = prediction.get("annotated_image")
                
                    if annotated_file is None:
                                        raise ValueError(
                            "annotated_image missing from detect_pothole() result"
                        )
                
                    annotated_file.seek(0)
                    image_content = ContentFile(annotated_file.read())
                
                else:
                    jpeg_file.seek(0)
                    image_content = ContentFile(jpeg_file.read())
                
                pothole.image.save(
                    filename,
                    image_content,
                    save=False
                )
                
                pothole.is_pothole = prediction["is_pothole"]
                pothole.label = prediction["label"]
                pothole.confidence = prediction["confidence"]
                
                pothole.save()
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


TEST_CAPTURE_TTL = 60
MAX_TEST_IMAGE_BYTES = 5 * 1024 * 1024
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
RGB565_BYTE_ORDER = "little"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def capture_test_image(request, device_id):
    """
    Request a single image from the selected ESP32-CAM.
    Does not create a Pothole or save an image file.
    """
    # TODO: Verify the logged-in user may access this device.
    try:
        device = Device.objects.get(
            device_id=device_id,
            is_active=True,
        )
    except Device.DoesNotExist:
        return Response(
            {"success": False, "error": "Device not found or inactive"},
            status=status.HTTP_404_NOT_FOUND,
        )

    capture_id = str(uuid.uuid4())
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return Response(
            {"success": False, "error": "WebSocket layer is not configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    cache.set(
        f"test_capture:{capture_id}",
        {
            "device_id": device.device_id,
            "status": "pending",
        },
        timeout=TEST_CAPTURE_TTL,
    )

    try:
        async_to_sync(channel_layer.group_send)(
            f"camera_{device.device_id}",
            {
                "type": "capture.request",
                "request_id": capture_id,
            },
        )
    except Exception:
        cache.delete(f"test_capture:{capture_id}")
        return Response(
            {"success": False, "error": "Could not send capture command"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "success": True,
            "capture_id": capture_id,
            "device_id": device.device_id,
            "status": "pending",
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser])
def receive_test_image(request, capture_id):
    """Receive raw RGB565 bytes, convert to JPEG, and cache temporarily."""

    capture_key = f"test_capture:{capture_id}"
    image_key = f"test_image:{capture_id}"

    # 1. Check capture request.
    capture = cache.get(capture_key)

    if not capture:
        return Response(
            {"success": False, "error": "Capture expired or not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 2. Authenticate device.
    device_id = request.headers.get("Device-ID")
    device_token = request.headers.get("Device-Token")

    if not device_id or not device_token:
        return Response(
            {"success": False, "error": "Device credentials required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        device = Device.objects.get(
            device_id=device_id,
            is_active=True,
        )
    except Device.DoesNotExist:
        return Response(
            {"success": False, "error": "Unknown device"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    provided_hash = hashlib.sha256(
        device_token.encode("utf-8")
    ).hexdigest()

    if not hmac.compare_digest(
        provided_hash,
        device.device_token_hash or "",
    ):
        return Response(
            {"success": False, "error": "Invalid device token"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if device.device_id != capture["device_id"]:
        return Response(
            {"success": False, "error": "Device does not match capture request"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3. Get uploaded raw RGB565 data.
    image_file = request.FILES.get("image")

    if image_file is None:
        return Response(
            {"success": False, "error": "Missing file field: image"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if image_file.size > MAX_TEST_IMAGE_BYTES:
        return Response(
            {"success": False, "error": "Image exceeds 5 MB"},
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    raw_bytes = image_file.read()

    expected_size = CAMERA_WIDTH * CAMERA_HEIGHT * 2

    if len(raw_bytes) != expected_size:
        return Response(
            {
                "success": False,
                "error": (
                    f"Invalid RGB565 size: expected {expected_size} bytes "
                    f"for {CAMERA_WIDTH}x{CAMERA_HEIGHT}, "
                    f"received {len(raw_bytes)} bytes"
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Convert raw RGB565 to JPEG.
    try:
        jpeg_buffer = rgb565_to_jpeg(
            raw_data=raw_bytes,
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            quality=85,
            byte_order='big',
        )
        jpeg_bytes = jpeg_buffer.getvalue()

    except (ValueError, TypeError) as exc:
        return Response(
            {"success": False, "error": f"Conversion failed: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("RGB565 conversion failed")
        return Response(
            {"success": False, "error": "Failed to convert RGB565 image"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 5. Cache the JPEG and update capture status.
    cache.set(
        image_key,
        jpeg_bytes,
        timeout=TEST_CAPTURE_TTL,
    )

    capture["status"] = "captured"

    cache.set(
        capture_key,
        capture,
        timeout=TEST_CAPTURE_TTL,
    )

    # 6. Update device activity.
    device.last_seen = timezone.now()
    device.save(update_fields=["last_seen"])

    return Response(
        {
            "success": True,
            "status": "captured",
            "format": "JPEG",
            "width": CAMERA_WIDTH,
            "height": CAMERA_HEIGHT,
            "raw_bytes": len(raw_bytes),
            "jpeg_bytes": len(jpeg_bytes),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_test_image(request, capture_id):
    """
    Return the temporary JPEG bytes for the React preview.
    """
    capture = cache.get(f"test_capture:{capture_id}")

    if not capture:
        return Response(
            {"success": False, "error": "Capture expired"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # TODO: Check that the authenticated user may access this device.
    image_bytes = cache.get(f"test_image:{capture_id}")

    if image_bytes is None:
        return Response(
            {"success": True, "status": capture["status"]},
            status=status.HTTP_202_ACCEPTED,
        )

    response = HttpResponse(
        image_bytes,
        content_type="image/jpeg",
    )
    response["Cache-Control"] = "no-store"
    return response
