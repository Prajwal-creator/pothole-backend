from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    ForgotPasswordView,
    VerifyOTPView,
    ResetPasswordView,
    MeView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


urlpatterns = [

    path(
        "register/",
        RegisterView.as_view(),
        name="register"
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login"
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),

    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password"
    ),

    path(
        "verify-otp/",
        VerifyOTPView.as_view(),
        name="verify-otp"
    ),

    path(
        "reset-password/",
        ResetPasswordView.as_view(),
        name="reset-password"
    ),

    path(
        "me/",
        MeView.as_view(),
        name="me"
    ),
]