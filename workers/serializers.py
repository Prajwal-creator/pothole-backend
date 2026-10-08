from rest_framework import serializers
from .models import Worker


class WorkerSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )

    email = serializers.EmailField(
        source='user.email',
        read_only=True
    )

    class Meta:
        model = Worker
        fields = [
            'employee_id',
            'full_name',
            'email',
            'status',
            'created_at',
            'updated_at',
        ]