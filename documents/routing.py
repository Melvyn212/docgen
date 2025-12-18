from django.urls import path

from .consumers import DocumentMetricsConsumer

websocket_urlpatterns = [
    path("ws/documents/metrics/", DocumentMetricsConsumer.as_asgi()),
]
