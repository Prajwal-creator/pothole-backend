from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "api/auth/",
        include("accounts.urls")
    ),
    
    path(
    'api/devices/',
    include('devices.urls')
     ),

     path(
    'api/',
     include('telemetry.urls')
     ),

     path(
    'api/workers/',
    include('workers.urls')
     ),

     path(
        "api/potholes/",
        include("potholes.urls")
    ),
    
]

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )