from django.urls import path
from .views import (
    DeviceCreateView,
    DeviceListView,
    DeviceDetailView,
    DeviceSuspendView,
    DeviceActivateView,
    DeviceRegenerateTokenView,
)


urlpatterns = [
    path(
        '',
        DeviceCreateView.as_view(),
        name='device-create'
    ),
    path(
        'list/',
        DeviceListView.as_view(),
        name='device-list'
    ),

    
    path(
        '<str:device_id>/',
        DeviceDetailView.as_view(),
        name='device-detail'
    ),

    
    path(
        '<str:device_id>/suspend/',
        DeviceSuspendView.as_view(),
        name='device-suspend'
    ),

    path(
        '<str:device_id>/activate/',
        DeviceActivateView.as_view(),
        name='device-activate'
    ),
    path(
       '<str:device_id>/regenerate-token/',
       DeviceRegenerateTokenView.as_view(),
       name='device-regenerate-token'
       ),
]