"""
WebSocket URL routing for Django Channels.
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Single file conversion progress
    re_path(
        r"ws/conversion/(?P<task_id>[^/]+)/$", consumers.ConversionConsumer.as_asgi()
    ),
    # Batch conversion progress
    re_path(
        r"ws/batch/(?P<batch_id>[^/]+)/$", consumers.BatchConversionConsumer.as_asgi()
    ),
]
