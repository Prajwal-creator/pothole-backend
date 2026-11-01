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
from django.db.models import Q
from .pagination import PotholePagination

#android imports

import os
import io
import hmac
import hashlib
import tempfile
import traceback

from PIL import Image, UnidentifiedImageError

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


class PotholeDetectView(APIView):

    parser_classes = [
    MultiPartParser,
    FormParser
   ]

    def post(self, request):

        # ==================================================
        # DEVICE AUTHENTICATION
        # ==================================================
        print("entered into an pothole sending image ....................................................")

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

# get request for potholes

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_potholes(request):
    queryset = (
        Pothole.objects
        .select_related("device")
        .all()
        .order_by("-detected_at")
    )

    # Filter by detection result
    detection = request.query_params.get(
        "is_pothole", ""
    ).strip().lower()

    if detection in ("true", "false"):
        queryset = queryset.filter(
            is_pothole=(detection == "true")
        )

    # Filter by severity
    severity = request.query_params.get("severity", "").strip()

    if severity and severity.lower() != "all":
        queryset = queryset.filter(severity__iexact=severity)

    # Filter by status
    pothole_status = request.query_params.get("status", "").strip()

    if pothole_status and pothole_status.lower() != "all":
        queryset = queryset.filter(status__iexact=pothole_status)

    # Search by pothole ID or device
    search = request.query_params.get("search", "").strip()

    if search:
        query = (
            Q(pothole_id__icontains=search)
            | Q(device__device_id__icontains=search)
            | Q(device__name__icontains=search)
        )

        try:
            coordinate = float(search)
            query |= (
                Q(latitude=coordinate)
                | Q(longitude=coordinate)
            )
        except ValueError:
            pass

        queryset = queryset.filter(query)

    # Pagination
    paginator = PotholePagination()
    page = paginator.paginate_queryset(queryset, request)

    serializer = PotholeSerializer(
        page,
        many=True,
        context={"request": request},
    )

    return paginator.get_paginated_response(serializer.data)

class AndroidPotholeDetectView(APIView):

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):

        print("\n========== ANDROID POTHOLE API ==========")

        # =========================================
        # 1. DEVICE AUTHENTICATION
        # =========================================

        print("STEP 1: Device authentication")

        device_id = request.headers.get("Android-Device-ID")
        device_token = request.headers.get("Android-Device-Token")

        if not device_id or not device_token:
            return Response({
                "success": False,
                "error": "Android device credentials are required"
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            device = Device.objects.get(device_id=device_id)

        except Device.DoesNotExist:
            return Response({
                "success": False,
                "error": "Unknown Android device"
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not device.is_active:
            return Response({
                "success": False,
                "error": "Android device is inactive"
            }, status=status.HTTP_403_FORBIDDEN)

        if not device.device_token_hash:
            return Response({
                "success": False,
                "error": "Device token is not configured"
            }, status=status.HTTP_401_UNAUTHORIZED)

        provided_hash = hashlib.sha256(
            device_token.encode("utf-8")
        ).hexdigest()

        if not hmac.compare_digest(
            provided_hash,
            device.device_token_hash
        ):
            return Response({
                "success": False,
                "error": "Invalid Android device token"
            }, status=status.HTTP_401_UNAUTHORIZED)

        print("DEVICE AUTHENTICATION SUCCESS")

        # =========================================
        # 2. RECEIVE JPEG IMAGE
        # =========================================

        print("STEP 2: Receiving image")

        image_file = request.FILES.get("image")

        if not image_file:
            return Response({
                "success": False,
                "error": "JPEG image is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        raw_image = image_file.read()

        print("IMAGE NAME:", image_file.name)
        print("IMAGE CONTENT TYPE:", image_file.content_type)
        print("IMAGE SIZE:", len(raw_image))
        print("JPEG HEADER:", raw_image[:10].hex())

        if not raw_image:
            return Response({
                "success": False,
                "error": "Uploaded image is empty"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not raw_image.startswith(b"\xff\xd8\xff"):
            return Response({
                "success": False,
                "error": "Uploaded file is not a JPEG image"
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================
        # 3. DECODE AND VALIDATE JPEG
        # =========================================

        print("STEP 3: JPEG validation")

        try:
            with Image.open(io.BytesIO(raw_image)) as img:

                print("IMAGE FORMAT:", img.format)
                print("IMAGE MODE:", img.mode)

                if img.format != "JPEG":
                    raise ValueError("Image format is not JPEG")

                img.load()

                width, height = img.size

                if width <= 0 or height <= 0:
                    raise ValueError("Invalid image dimensions")

            print("JPEG VALIDATION SUCCESS")
            print("WIDTH:", width)
            print("HEIGHT:", height)

        except Exception as e:

            print("JPEG VALIDATION ERROR:", repr(e))
            traceback.print_exc()

            return Response({
                "success": False,
                "error": "JPEG image validation failed",
                "details": str(e),
                "error_type": type(e).__name__
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================
        # 4. YOLO INFERENCE
        # =========================================

        print("STEP 4: Starting YOLO inference")

        temp_image_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False
            ) as temp_file:

                temp_file.write(raw_image)
                temp_image_path = temp_file.name

            prediction = detect_pothole(
                image_path=temp_image_path,
                threshold=0.10
            )

            print("YOLO RESULT:", prediction)

            is_pothole = bool(prediction["is_pothole"])
            label = prediction["label"]
            yolo_confidence = float(prediction["confidence"])

            print("POTHOLE DETECTED:", is_pothole)
            print("LABEL:", label)
            print("CONFIDENCE:", yolo_confidence)

        except Exception as e:

            print("YOLO INFERENCE ERROR:", repr(e))
            traceback.print_exc()

            return Response({
                "success": False,
                "error": "YOLO inference failed",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:

            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

        # =========================================
        # 5. GPS DATA
        # =========================================

        print("STEP 5: Reading GPS data")

        try:
            latitude = float(request.data.get("latitude"))
            longitude = float(request.data.get("longitude"))

            speed = float(request.data.get("speed") or 0)
            accuracy = float(request.data.get("accuracy") or 0)
            satellites = int(request.data.get("satellites") or 0)

        except (TypeError, ValueError) as e:

            return Response({
                "success": False,
                "error": "Invalid GPS data",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude <= 90):
            return Response({
                "success": False,
                "error": "Latitude must be between -90 and 90"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not (-180 <= longitude <= 180):
            return Response({
                "success": False,
                "error": "Longitude must be between -180 and 180"
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================
        # 6. ACCELEROMETER DATA
        # =========================================

        print("STEP 6: Reading accelerometer data")

        try:
            ax = float(request.data.get("ax") or 0)
            ay = float(request.data.get("ay") or 0)
            az = float(request.data.get("az") or 0)

        except (TypeError, ValueError) as e:

            return Response({
                "success": False,
                "error": "Invalid accelerometer data",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================
        # 7. POTHOLE INFORMATION
        # =========================================

        severity = request.data.get("severity") or "Medium"

        try:
            confidence = yolo_confidence

        except (TypeError, ValueError) as e:

            return Response({
                "success": False,
                "error": "Invalid confidence value",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # =========================================
        # 8. SAVE POTHOLE AND IMAGE
        # =========================================

        print("STEP 7: Saving pothole")

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

                pothole.is_pothole = is_pothole
                pothole.label = label

                pothole.save()

                filename = f"{pothole.pothole_id}.jpg"

                # Save the original JPEG first.
                # This avoids assuming annotated_image is file-like.
                pothole.image.save(
                    filename,
                    ContentFile(raw_image),
                    save=False
                )

                pothole.save()

                device.last_seen = timezone.now()

                device.save(
                    update_fields=["last_seen"]
                )

            print("DATABASE SAVE SUCCESS")

        except Exception as e:

            print("DATABASE ERROR:", repr(e))
            traceback.print_exc()

            return Response({
                "success": False,
                "error": "Database save failed",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # =========================================
        # 9. API RESPONSE
        # =========================================

        serializer = PotholeSerializer(
            pothole,
            context={"request": request}
        )

        print("ANDROID POTHOLE API SUCCESS")
        print("========================================")

        return Response({

            "success": True,

            "message": "Android pothole detection successful",

            "image_width": width,
            "image_height": height,

            "pothole": serializer.data

        }, status=status.HTTP_201_CREATED)

#this is the potholes count

class TotalPotholesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total = Pothole.objects.count()

        return Response({
            "success": True,
            "totalPotholes": total
        })

class DetectedTodayAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()

        total = Pothole.objects.filter(
            detected_at__date=today
        ).count()

        return Response({
            "success": True,
            "detectedToday": total,
            "date": today.isoformat()
        })

from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Pothole
from datetime import timedelta
from django.db.models import Count
from django.db.models.functions import TruncDate


class PotholeSeverityCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        results = (
            Pothole.objects
            .values("severity")
            .annotate(total=Count("id"))
        )

        for item in results:
            severity = (item["severity"] or "").strip().lower()

            if severity in severity_counts:
                severity_counts[severity] += item["total"]

        return Response({
            "success": True,
            "severityCounts": severity_counts,
            "total": sum(severity_counts.values())
        })


class PotholeDetectionTrendAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 14))
        except (TypeError, ValueError):
            return Response({
                "success": False,
                "error": "days must be a valid integer"
            }, status=400)

        if days < 1 or days > 90:
            return Response({
                "success": False,
                "error": "days must be between 1 and 90"
            }, status=400)

        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)

        daily_counts = (
            Pothole.objects
            .filter(
                detected_at__date__range=(start_date, today)
            )
            .annotate(day=TruncDate("detected_at"))
            .values("day")
            .annotate(potholes=Count("id"))
            .order_by("day")
        )

        counts_by_date = {
            item["day"]: item["potholes"]
            for item in daily_counts
        }

        trend = []

        for offset in range(days):
            current_date = start_date + timedelta(days=offset)

            trend.append({
                "day": current_date.isoformat(),
                "potholes": counts_by_date.get(current_date, 0)
            })

        return Response({
            "success": True,
            "days": days,
            "total": sum(item["potholes"] for item in trend),
            "trend": trend
        })


class PotholeMapAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Fetch ALL database records
        potholes = Pothole.objects.all().order_by("-detected_at")

        # Serialize all records
        serializer = PotholeSerializer(
            potholes,
            many=True,
            context={"request": request}
        )

        # Severity counts across all records
        severity_counts = {
            "Low": 0,
            "Medium": 0,
            "High": 0,
            "Critical": 0,
        }

        severity_data = (
            potholes.values("severity")
            .annotate(total=Count("id"))
        )

        for item in severity_data:
            severity = item["severity"]

            if severity in severity_counts:
                severity_counts[severity] = item["total"]

        return Response({
            "success": True,
            "total": potholes.count(),
            "severity_counts": severity_counts,
            "potholes": serializer.data,
        })


import math

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Pothole
from .serializers import PotholeSerializer


def calculate_distance_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0088

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


class NearbyPotholesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_lat = float(request.query_params.get("latitude"))
            user_lon = float(request.query_params.get("longitude"))
            radius_km = float(request.query_params.get("radius_km", 5))
        except (TypeError, ValueError):
            return Response({
                "success": False,
                "error": "Valid latitude, longitude and radius_km are required."
            }, status=400)

        if not -90 <= user_lat <= 90:
            return Response({
                "success": False,
                "error": "Invalid latitude."
            }, status=400)

        if not -180 <= user_lon <= 180:
            return Response({
                "success": False,
                "error": "Invalid longitude."
            }, status=400)

        if radius_km not in (1, 5, 10, 25):
            return Response({
                "success": False,
                "error": "Radius must be 1, 5, 10 or 25 km."
            }, status=400)

        # Fetch all records with usable GPS coordinates.
        potholes = (
            Pothole.objects
            .exclude(latitude=0, longitude=0)
            .order_by("-detected_at")
        )

        serializer = PotholeSerializer(
            potholes,
            many=True,
            context={"request": request}
        )

        nearby = []

        for pothole in serializer.data:
            try:
                pothole_lat = float(pothole["latitude"])
                pothole_lon = float(pothole["longitude"])

                if not (
                    -90 <= pothole_lat <= 90
                    and -180 <= pothole_lon <= 180
                ):
                    continue

                distance = calculate_distance_km(
                    user_lat,
                    user_lon,
                    pothole_lat,
                    pothole_lon
                )

                if distance <= radius_km:
                    item = dict(pothole)
                    item["distance_km"] = round(distance, 2)
                    nearby.append((distance, item))

            except (TypeError, ValueError, KeyError):
                continue

        # Nearest pothole first.
        nearby.sort(key=lambda item: item[0])

        results = [item[1] for item in nearby]

        severity_counts = {
            "Low": 0,
            "Medium": 0,
            "High": 0,
            "Critical": 0,
        }

        for pothole in results:
            severity = pothole.get("severity")

            if severity in severity_counts:
                severity_counts[severity] += 1

        return Response({
            "success": True,
            "user_location": {
                "latitude": user_lat,
                "longitude": user_lon,
            },
            "radius_km": radius_km,
            "total": len(results),
            "severity_counts": severity_counts,
            "potholes": results,
        })