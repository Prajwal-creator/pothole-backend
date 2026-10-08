from django.urls import path

from .views import DeviceTelemetryView


urlpatterns = [

    path(
        'devices/<str:device_id>/data/',
        DeviceTelemetryView.as_view(),
        name='device-telemetry'
    ),

]