from django.urls import path
from .views import PotholeDetectView
from .views import capture_test_image
from .views import receive_test_image
from .views import get_test_image


urlpatterns = [

    path(
        "detect/",
        PotholeDetectView.as_view(),
        name="pothole-detect"
    ),
    path(
    "devices/<str:device_id>/capture-test/",
    capture_test_image,

    ),
    path(
        "capture-test/<uuid:capture_id>/upload/",
        receive_test_image,

    ),
    path(
        "capture-test/<uuid:capture_id>/image/",
        get_test_image,

    ),

]