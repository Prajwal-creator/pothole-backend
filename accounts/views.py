import secrets
import hashlib
import random
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, PasswordResetOTP
from .serializers import (
    RegisterSerializer,
    UserSerializer,
)


# ============================================================
# REGISTER
# ============================================================

class RegisterView(APIView):

    permission_classes = []

    def post(self, request):

        serializer = RegisterSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


# ============================================================
# LOGIN
# ============================================================

class LoginView(APIView):

    permission_classes = []

    def post(self, request):

        email = request.data.get("email", "").lower().strip()
        password = request.data.get("password", "")

        if not email or not password:

            return Response(
                {
                    "message": "Email and password are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            request,
            email=email,
            password=password
        )

        if user is None:

            return Response(
                {
                    "message": "Invalid email or password."
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:

            return Response(
                {
                    "message": "This account is disabled."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",

                "access": str(refresh.access_token),

                "refresh": str(refresh),

                "user": UserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# FORGOT PASSWORD
# ============================================================

class ForgotPasswordView(APIView):

    permission_classes = []

    def post(self, request):

        email = request.data.get(
            "email",
            ""
        ).lower().strip()

        if not email:

            return Response(
                {
                    "message": "If an account exists, an OTP has been sent."
                },
                status=status.HTTP_200_OK
            )

        # Generic response prevents email enumeration
        user = User.objects.filter(
            email=email
        ).first()

        if user is None:

            return Response(
                {
                    "message": "If an account exists, an OTP has been sent."
                },
                status=status.HTTP_200_OK
            )

        now = timezone.now()

        # Prevent OTP spam
        recent_otp = PasswordResetOTP.objects.filter(
            email=email,
            created_at__gte=now - timedelta(seconds=30)
        ).exists()

        if recent_otp:

            return Response(
                {
                    "message": "Please wait before requesting another OTP."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Invalidate previous OTPs
        PasswordResetOTP.objects.filter(
            email=email,
            verified=False
        ).update(
            verified=True
        )

        # Generate 6 digit OTP
        otp = f"{random.randint(100000, 999999)}"

        otp_hash = make_password(otp)

        expires_at = now + timedelta(
            minutes=2
        )

        PasswordResetOTP.objects.create(
            email=email,
            otp_hash=otp_hash,
            expires_at=expires_at
        )

        # Send OTP
        send_mail(
            subject="RoadGuard AI Password Reset OTP",

            message=(
                f"Your RoadGuard AI password reset OTP is: {otp}\n\n"
                "This OTP is valid for 30 seconds.\n"
                "Do not share this OTP with anyone."
            ),

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=[email],

            fail_silently=False
        )

        return Response(
            {
                "message": "If an account exists, an OTP has been sent."
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# VERIFY OTP
# ============================================================

class VerifyOTPView(APIView):

    permission_classes = []

    def post(self, request):

        email = request.data.get(
            "email",
            ""
        ).lower().strip()

        otp = request.data.get(
            "otp",
            ""
        ).strip()

        if not email or not otp:

            return Response(
                {
                    "message": "Email and OTP are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        reset_request = PasswordResetOTP.objects.filter(
            email=email,
            verified=False
        ).order_by("-created_at").first()

        if reset_request is None:

            return Response(
                {
                    "message": "Invalid or expired OTP."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check expiry first
        if reset_request.is_expired():

            reset_request.verified = True
            reset_request.save(
                update_fields=["verified"]
            )

            return Response(
                {
                    "message": "OTP has expired."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Maximum attempts
        if reset_request.attempts >= 5:

            reset_request.verified = True
            reset_request.save(
                update_fields=["verified"]
            )

            return Response(
                {
                    "message": "Too many incorrect attempts."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Increase attempts
        reset_request.attempts += 1

        reset_request.save(
            update_fields=["attempts"]
        )

        # Verify hashed OTP
        if not check_password(
            otp,
            reset_request.otp_hash
        ):

            return Response(
                {
                    "message": "Invalid OTP."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)

        reset_token_hash = hashlib.sha256(
            reset_token.encode()
        ).hexdigest()

        reset_request.verified = True

        reset_request.reset_token_hash = reset_token_hash

        reset_request.reset_token_expires_at = (
            timezone.now() + timedelta(minutes=10)
        )

        reset_request.save(
            update_fields=[
                "verified",
                "reset_token_hash",
                "reset_token_expires_at"
            ]
        )

        return Response(
            {
                "message": "OTP verified successfully.",

                "reset_token": reset_token
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# RESET PASSWORD
# ============================================================

class ResetPasswordView(APIView):

    permission_classes = []

    def post(self, request):

        email = request.data.get(
            "email",
            ""
        ).lower().strip()

        reset_token = request.data.get(
            "reset_token",
            ""
        )

        new_password = request.data.get(
            "new_password",
            ""
        )

        confirm_password = request.data.get(
            "confirm_password",
            ""
        )

        if not all([
            email,
            reset_token,
            new_password,
            confirm_password
        ]):

            return Response(
                {
                    "message": "All fields are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:

            return Response(
                {
                    "message": "Passwords do not match."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:

            return Response(
                {
                    "message": "Password must be at least 6 characters."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        token_hash = hashlib.sha256(
            reset_token.encode()
        ).hexdigest()

        reset_request = PasswordResetOTP.objects.filter(
            email=email,
            verified=True,
            reset_token_hash=token_hash
        ).order_by("-created_at").first()

        if reset_request is None:

            return Response(
                {
                    "message": "Invalid reset token."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check reset token expiry
        if (
            reset_request.reset_token_expires_at is None
            or
            timezone.now() >= reset_request.reset_token_expires_at
        ):

            return Response(
                {
                    "message": "Reset token has expired."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            email=email
        ).first()

        if user is None:

            return Response(
                {
                    "message": "Unable to reset password."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(
            new_password
        )

        user.save(
            update_fields=["password"]
        )

        # Destroy reset token
        reset_request.reset_token_hash = None
        reset_request.reset_token_expires_at = None

        reset_request.save(
            update_fields=[
                "reset_token_hash",
                "reset_token_expires_at"
            ]
        )

        return Response(
            {
                "message": "Password reset successfully."
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# CURRENT USER
# ============================================================

class MeView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        return Response(
            UserSerializer(
                request.user
            ).data
        )
