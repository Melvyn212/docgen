from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from documents.api import (
    GenerateBulletinView,
    GenerateHonorView,
    DownloadDocumentView,
    ResetMetricsView,
    StreamBulletinView,
    StreamHonorView,
    CreateBatchView,
    BatchStatusView,
    BatchDownloadView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/documents/bulletin/", GenerateBulletinView.as_view(), name="generate-bulletin"),
    path("api/documents/honor-board/", GenerateHonorView.as_view(), name="generate-honor"),
    path("api/documents/bulletin/stream/", StreamBulletinView.as_view(), name="stream-bulletin"),
    path("api/documents/honor-board/stream/", StreamHonorView.as_view(), name="stream-honor"),
    path("api/documents/<int:pk>/download/", DownloadDocumentView.as_view(), name="download-document"),
    path("api/batches/", CreateBatchView.as_view(), name="create-batch"),
    path("api/batches/<int:pk>/", BatchStatusView.as_view(), name="batch-status"),
    path("api/batches/<int:pk>/download/", BatchDownloadView.as_view(), name="batch-download"),
    path("api/metrics/reset/", ResetMetricsView.as_view(), name="reset-metrics"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Ensure media files are served even if DEBUG is False during local dev.
if not settings.DEBUG and settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += [
        re_path(r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"), serve, {"document_root": settings.MEDIA_ROOT}),
    ]
