import secrets
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import (
    make_password,
    check_password,
)
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
    AllowAny,
)
from .models import Worker, WorkerInvitation
from .serializers import WorkerSerializer


User = get_user_model()


# ============================================================
# ADMIN - CREATE WORKER
# ============================================================

class WorkerCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def post(self, request):

        full_name = request.data.get(
            'full_name',
            ''
        ).strip()

        email = request.data.get(
            'email',
            ''
        ).strip().lower()

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not full_name:

            return Response(
                {
                    'message': 'Full name is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not email:

            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Check existing email
        # ----------------------------------------------------

        if User.objects.filter(
            email=email
        ).exists():

            return Response(
                {
                    'message': (
                        'A user with this email already exists.'
                    )
                },
                status=status.HTTP_409_CONFLICT
            )

        # ----------------------------------------------------
        # Generate employee ID
        # ----------------------------------------------------

        employee_id = self.generate_employee_id()

        # ----------------------------------------------------
        # Create User
        # ----------------------------------------------------

        user = User(
            email=email,
            full_name=full_name,
            phone=''
        )

        # Worker cannot login yet
        user.is_active = False

        # No usable password yet
        user.set_unusable_password()

        user.save()

        # ----------------------------------------------------
        # Create Worker
        # ----------------------------------------------------

        worker = Worker.objects.create(
            user=user,
            employee_id=employee_id,
            status='INVITED'
        )

        # ----------------------------------------------------
        # Send invitation email
        # ----------------------------------------------------

        self.send_invitation_email(worker)

        serializer = WorkerSerializer(worker)

        return Response(
            {
                'message': 'Worker created successfully.',
                'worker': serializer.data,
            },
            status=status.HTTP_201_CREATED
        )

    # --------------------------------------------------------
    # Generate employee ID
    # --------------------------------------------------------

    def generate_employee_id(self):

        while True:

            employee_id = (
                f"RG-W-{secrets.randbelow(900000) + 100000}"
            )

            if not Worker.objects.filter(
                employee_id=employee_id
            ).exists():

                return employee_id

    # --------------------------------------------------------
    # Send invitation email
    # --------------------------------------------------------

    def send_invitation_email(self, worker):

        frontend_url = getattr(
            settings,
            'FRONTEND_URL',
            'http://localhost:5173'
        )

        login_url = (
            f"{frontend_url}/worker/login"
        )

        subject = "Worker Account Invitation"

        message = f"""
Hello {worker.user.full_name},

You have been added as a worker.

Employee ID:
{worker.employee_id}

Registered Email:
{worker.user.email}

Worker Login:
{login_url}

To activate your account:

1. Open the worker login page.
2. Enter your registered email.
3. Request the OTP.
4. Enter the OTP sent to your email.
5. Create your new password.
6. Login to your worker dashboard.

If you did not expect this invitation,
please contact the administrator.

Regards,
Admin
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                None
            ),
            recipient_list=[
                worker.user.email
            ],
            fail_silently=False,
        )


# ============================================================
# ADMIN - LIST WORKERS
# ============================================================

class WorkerListView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def get(self, request):

        workers = Worker.objects.select_related(
            'user'
        ).order_by(
            '-created_at'
        )

        serializer = WorkerSerializer(
            workers,
            many=True
        )

        return Response(
            {
                'workers': serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# ADMIN - GET SINGLE WORKER
# ============================================================

class WorkerDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def get(self, request, employee_id):

        worker = get_object_or_404(
            Worker.objects.select_related('user'),
            employee_id=employee_id
        )

        serializer = WorkerSerializer(worker)

        return Response(
            {
                'worker': serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# ADMIN - DELETE WORKER
# ============================================================

class WorkerDeleteView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdminUser,
    ]

    def delete(self, request, employee_id):

        worker = get_object_or_404(
            Worker,
            employee_id=employee_id
        )

        worker.delete()

        return Response(
            {
                'message': 'Worker deleted successfully.'
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# WORKER - REQUEST OTP
# ============================================================

class WorkerRequestOTPView(APIView):

    permission_classes = [
        AllowAny,
    ]

    def post(self, request):

        email = request.data.get(
            'email',
            ''
        ).strip().lower()

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not email:

            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Find worker
        # ----------------------------------------------------

        try:

            worker = Worker.objects.select_related(
                'user'
            ).get(
                user__email=email
            )

        except Worker.DoesNotExist:

            return Response(
                {
                    'message': 'Worker account not found.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ----------------------------------------------------
        # Worker must be INVITED
        # ----------------------------------------------------

        if worker.status != 'INVITED':

            return Response(
                {
                    'message': (
                        'This worker account is not '
                        'awaiting activation.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Generate OTP
        # ----------------------------------------------------

        otp = f"{secrets.randbelow(1000000):06d}"
        print(otp)
        # ----------------------------------------------------
        # Create / update invitation
        # ----------------------------------------------------

        expires_at = timezone.now() + timedelta(minutes=5)

        invitation, created = WorkerInvitation.objects.update_or_create(
             worker=worker,
             defaults={
            'otp_hash': make_password(otp),
            'expires_at': expires_at,
            'verified': False,
            'attempts': 0,
            'token_hash': None,
            }
         )

        # ----------------------------------------------------
        # Send OTP email
        # ----------------------------------------------------

        subject = "Worker Verification OTP"

        message = f"""
Hello {worker.user.full_name},

Your worker verification OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this OTP,
please ignore this email.

Regards,
Admin
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                None
            ),
            recipient_list=[
                worker.user.email
            ],
            fail_silently=False,
        )

        return Response(
            {
                'message': 'OTP sent successfully.'
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# WORKER - VERIFY OTP
# ============================================================

class WorkerVerifyOTPView(APIView):

    permission_classes = [
        AllowAny,
    ]

    def post(self, request):

        email = request.data.get(
            'email',
            ''
        ).strip().lower()

        otp = request.data.get(
            'otp',
            ''
        ).strip()

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not email:

            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not otp:

            return Response(
                {
                    'message': 'OTP is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Find invitation
        # ----------------------------------------------------

        try:

            invitation = (
                WorkerInvitation.objects
                .select_related(
                    'worker__user'
                )
                .get(
                    worker__user__email=email
                )
            )

        except WorkerInvitation.DoesNotExist:

            return Response(
                {
                    'message': 'Invalid OTP request.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Check expiry
        # ----------------------------------------------------

        if invitation.expires_at < timezone.now():

            return Response(
                {
                    'message': 'OTP has expired.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Check attempts
        # ----------------------------------------------------

        if invitation.attempts >= 5:

            return Response(
                {
                    'message': (
                        'Too many incorrect attempts. '
                        'Please request a new OTP.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # ----------------------------------------------------
        # Increase attempt count
        # ----------------------------------------------------

        invitation.attempts += 1

        # ----------------------------------------------------
        # Check OTP
        # ----------------------------------------------------

        if not check_password(
            otp,
            invitation.otp_hash
        ):

            invitation.save(
                update_fields=[
                    'attempts'
                ]
            )

            return Response(
                {
                    'message': 'Invalid OTP.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # OTP correct
        # ----------------------------------------------------

        reset_token = secrets.token_urlsafe(48)

        invitation.token_hash = make_password(
            reset_token
        )

        invitation.verified = True

        invitation.save()

        return Response(
            {
                'message': 'OTP verified successfully.',
                'reset_token': reset_token,
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# WORKER - SET FIRST PASSWORD
# ============================================================

class WorkerSetPasswordView(APIView):

    permission_classes = [
        AllowAny,
    ]

    def post(self, request):

        email = request.data.get(
            'email',
            ''
        ).strip().lower()

        reset_token = request.data.get(
            'reset_token',
            ''
        ).strip()

        new_password = request.data.get(
            'new_password',
            ''
        )

        confirm_password = request.data.get(
            'confirm_password',
            ''
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not email:

            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token:

            return Response(
                {
                    'message': 'Reset token is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not new_password:

            return Response(
                {
                    'message': 'New password is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not confirm_password:

            return Response(
                {
                    'message': (
                        'Confirm password is required.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:

            return Response(
                {
                    'message': 'Passwords do not match.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Basic password validation
        # ----------------------------------------------------

        if len(new_password) < 8:

            return Response(
                {
                    'message': (
                        'Password must contain '
                        'at least 8 characters.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Find invitation
        # ----------------------------------------------------

        try:

            invitation = (
                WorkerInvitation.objects
                .select_related(
                    'worker__user'
                )
                .get(
                    worker__user__email=email
                )
            )

        except WorkerInvitation.DoesNotExist:

            return Response(
                {
                    'message': 'Invalid password setup request.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # OTP must already be verified
        # ----------------------------------------------------

        if not invitation.verified:

            return Response(
                {
                    'message': (
                        'OTP verification is required.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Reset token must exist
        # ----------------------------------------------------

        if not invitation.token_hash:

            return Response(
                {
                    'message': 'Invalid reset token.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Check reset token
        # ----------------------------------------------------

        if not check_password(
            reset_token,
            invitation.token_hash
        ):

            return Response(
                {
                    'message': 'Invalid reset token.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----------------------------------------------------
        # Get user
        # ----------------------------------------------------

        worker = invitation.worker

        user = worker.user

        # ----------------------------------------------------
        # Set password
        # ----------------------------------------------------

        user.set_password(
            new_password
        )

        user.is_active = True

        user.save()

        # ----------------------------------------------------
        # Activate worker
        # ----------------------------------------------------

        worker.status = 'ACTIVE'

        worker.save()

        # ----------------------------------------------------
        # Invalidate token
        # ----------------------------------------------------

        invitation.token_hash = None

        invitation.verified = False

        invitation.otp_hash = ''

        invitation.attempts = 0

        invitation.save()

        return Response(
            {
                'message': (
                    'Password created successfully. '
                    'Your worker account is now active.'
                )
            },
            status=status.HTTP_200_OK
        )