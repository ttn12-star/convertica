from django.contrib import admin
from django.urls import path, include
from utils_site.settings import DEBUG
from utils_site.swagger import schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('src.urls')),
]

if DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    ]