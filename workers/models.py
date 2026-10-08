from django.conf import settings
from django.db import models


class Worker(models.Model):

    STATUS_CHOICES = [
        ('INVITED', 'Invited'),
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='worker_profile'
    )

    employee_id = models.CharField(
        max_length=50,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='INVITED'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.full_name} ({self.employee_id})"


class WorkerInvitation(models.Model):

    worker = models.OneToOneField(
        Worker,
        on_delete=models.CASCADE,
        related_name='invitation'
    )

    otp_hash = models.CharField(
        max_length=128
    )

    token_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True
    )

    expires_at = models.DateTimeField()

    verified = models.BooleanField(
        default=False
    )

    attempts = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Invitation - {self.worker.user.email}"