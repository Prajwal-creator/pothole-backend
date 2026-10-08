from django.urls import path

from .views import PotholeDetectView


urlpatterns = [

    path(
        "detect/",
        PotholeDetectView.as_view(),
        name="pothole-detect"
    ),

]