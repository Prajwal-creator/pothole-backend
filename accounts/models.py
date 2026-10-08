from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )


class User(AbstractUser):
    username = None

    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class PasswordResetOTP(models.Model):

    email = models.EmailField(db_index=True)

    otp_hash = models.CharField(max_length=128)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(default=0)

    verified = models.BooleanField(default=False)

    reset_token_hash = models.CharField(
        max_length=128,
        blank=True,
        null=True
    )

    reset_token_expires_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def is_expired(self):
        return timezone.now() >= self.expires_at