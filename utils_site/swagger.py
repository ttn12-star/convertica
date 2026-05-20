# myproject/swagger.py
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Convertica API",
        default_version="v1",
        description=(
            "Programmatic access to 30+ PDF/image conversion tools. "
            "Authentication via API key (issued in your dashboard at "
            "https://convertica.net/users/api-keys/). "
            "Subscription required."
        ),
        contact=openapi.Contact(email="support@convertica.net"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
