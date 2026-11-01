from django.urls import path
from .views import PotholeDetectView
from .views import capture_test_image
from .views import receive_test_image
from .views import get_test_image
from .views import get_potholes
from .views import AndroidPotholeDetectView
from .views import TotalPotholesAPIView
from .views import DetectedTodayAPIView
from .views import PotholeSeverityCountAPIView
from .views import PotholeDetectionTrendAPIView
from .views import PotholeMapAPIView
from .views import NearbyPotholesAPIView


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
    path("", get_potholes, name="get-potholes"),
      path(
        "android/detect/",
         AndroidPotholeDetectView.as_view(),
         name="android-pothole-detect"
      ),
        path(
        "total/",
        TotalPotholesAPIView.as_view(),
        name="total-potholes"
    ),
    path(
       "detected-today/",
       DetectedTodayAPIView.as_view(),
       name="detected-today"
       ),
    path(
    "severity-counts/",
    PotholeSeverityCountAPIView.as_view(),
    name="pothole-severity-counts"
     ),
      path(
        "detection-trend/",
        PotholeDetectionTrendAPIView.as_view(),
        name="pothole-detection-trend"
    ),
    path(
        "map/",
        PotholeMapAPIView.as_view(),
        name="pothole-map"
    ),
     path(
        "nearby/",
        NearbyPotholesAPIView.as_view(),
        name="nearby-potholes"
    ),
      
]