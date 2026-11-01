from django.urls import path

from .views import (
    WorkerCreateView,
    WorkerListView,
    WorkerDetailView,
    WorkerDeleteView,
    WorkerRequestOTPView,
    WorkerVerifyOTPView,
    WorkerSetPasswordView,
)
from .views import WorkerLoginView
from .views import WorkerMeView


urlpatterns = [

    # Admin
    path(
        '',
        WorkerCreateView.as_view(),
        name='worker-create'
    ),

    path(
        'list/',
        WorkerListView.as_view(),
        name='worker-list'
    ),

    path(
        '<str:employee_id>/',
        WorkerDetailView.as_view(),
        name='worker-detail'
    ),

    path(
        '<str:employee_id>/delete/',
        WorkerDeleteView.as_view(),
        name='worker-delete'
    ),

    path(
        'auth/request-otp/',
        WorkerRequestOTPView.as_view(),
        name='worker-request-otp'
    ),

    path(
        'auth/verify-otp/',
        WorkerVerifyOTPView.as_view(),
        name='worker-verify-otp'
    ),

    path(
        'auth/set-password/',
        WorkerSetPasswordView.as_view(),
        name='worker-set-password'
    ),
    path(
        "auth/login/",
        WorkerLoginView.as_view(),
        name="worker-login",
    ),
    path(
    "auth/me/",
    WorkerMeView.as_view(),
    name="worker-me",
    ),
    
]