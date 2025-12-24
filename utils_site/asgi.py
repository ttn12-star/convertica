"""
ASGI config for utils_site project.

It exposes the ASGI callable as a module-level variable named ``application``.

Supports both HTTP and WebSocket protocols via Django Channels.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utils_site.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import Channels components after Django is initialized
try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from src.api.routing import websocket_urlpatterns

    # Configure ASGI application with WebSocket support
    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        }
    )
except ImportError:
    # Fallback to HTTP-only if Channels is not installed
    application = django_asgi_app
