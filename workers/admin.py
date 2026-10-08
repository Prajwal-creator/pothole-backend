from django.contrib import admin
from .models import Worker, WorkerInvitation


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):

    list_display = (
        'employee_id',
        'user',
        'status',
        'created_at',
    )

    search_fields = (
        'employee_id',
        'user__email',
        'user__full_name',
    )

    list_filter = (
        'status',
        'created_at',
    )


@admin.register(WorkerInvitation)
class WorkerInvitationAdmin(admin.ModelAdmin):

    list_display = (
        'worker',
        'verified',
        'expires_at',
        'created_at',
    )

    search_fields = (
        'worker__user__email',
    )

    list_filter = (
        'verified',
        'created_at',
    )