from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import User


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=6
    )

    confirmPassword = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = User

        fields = [
            "fullName",
            "email",
            "phone",
            "password",
            "confirmPassword",
        ]

    fullName = serializers.CharField(
        source="full_name"
    )

    def validate_email(self, value):

        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def validate(self, data):

        if data["password"] != data["confirmPassword"]:
            raise serializers.ValidationError({
                "confirmPassword": "Passwords do not match."
            })

        return data

    def create(self, validated_data):

        validated_data.pop("confirmPassword")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        return user


class UserSerializer(serializers.ModelSerializer):

    fullName = serializers.CharField(
        source="full_name"
    )

    class Meta:
        model = User

        fields = [
            "id",
            "fullName",
            "email",
            "phone",
        ]