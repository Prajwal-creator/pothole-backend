import hashlib
import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Device
from .serializers import DeviceSerializer


class DeviceCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request):

        device_id = request.data.get("device_id", "").strip()
        name = request.data.get("name", "").strip()

        if not device_id:
            return Response(
                {
                    "message": "device_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not name:
            return Response(
                {
                    "message": "name is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if Device.objects.filter(
            device_id=device_id
        ).exists():

            return Response(
                {
                    "message": "Device with this device_id already exists."
                },
                status=status.HTTP_409_CONFLICT
            )

        # Generate secure device token
        raw_token = secrets.token_urlsafe(32)

        # Store only hash in database
        token_hash = hashlib.sha256(
            raw_token.encode()
        ).hexdigest()

        device = Device.objects.create(
            device_id=device_id,
            name=name,
            device_token_hash=token_hash,
        )

        serializer = DeviceSerializer(device)

        return Response(
            {
                "message": "Device created successfully.",
                "device": serializer.data,
                "device_token": raw_token,
            },
            status=status.HTTP_201_CREATED
        )

class DeviceListView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def get(self, request):

        devices = Device.objects.all().order_by('-created_at')

        serializer = DeviceSerializer(
            devices,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class DeviceDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def get(self, request, device_id):

        try:
            device = Device.objects.get(
                device_id=device_id
            )

        except Device.DoesNotExist:

            return Response(
                {
                    "message": "Device not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DeviceSerializer(device)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class DeviceSuspendView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, device_id):

        try:
            device = Device.objects.get(
                device_id=device_id
            )

        except Device.DoesNotExist:

            return Response(
                {
                    "message": "Device not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        device.is_active = False
        device.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Device suspended successfully.",
                "device_id": device.device_id,
                "is_active": device.is_active
            },
            status=status.HTTP_200_OK
        )

class DeviceActivateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, device_id):

        try:
            device = Device.objects.get(
                device_id=device_id
            )

        except Device.DoesNotExist:

            return Response(
                {
                    "message": "Device not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        device.is_active = True
        device.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Device activated successfully.",
                "device_id": device.device_id,
                "is_active": device.is_active
            },
            status=status.HTTP_200_OK
        )

class DeviceRegenerateTokenView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request, device_id):

        try:
            device = Device.objects.get(
                device_id=device_id
            )

        except Device.DoesNotExist:

            return Response(
                {
                    "message": "Device not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate new secure token
        new_token = secrets.token_urlsafe(32)

        # Hash token before storing
        new_token_hash = hashlib.sha256(
            new_token.encode()
        ).hexdigest()

        # Replace old token hash
        device.device_token_hash = new_token_hash

        device.save(
            update_fields=[
                "device_token_hash"
            ]
        )

        return Response(
            {
                "message": "Device token regenerated successfully.",

                "device_id": device.device_id,

                # Return raw token only once
                "device_token": new_token,
            },
            status=status.HTTP_200_OK
        )