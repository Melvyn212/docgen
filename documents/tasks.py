from pathlib import Path
import logging
import os
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from documents.models import Document
from documents.services.builder import build_context
from documents.services.latex_renderer import LatexRenderer
from documents.services.storage import store_pdf
from documents.services.metrics import mark_ready, mark_failed

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, max_retries=3)
def generate_document(self, document_id: int):
    doc = Document.objects.select_related("student__klass__school").get(id=document_id)
    logger.info("Start generate_document", extra={"document_id": document_id, "doc_type": doc.doc_type, "term": doc.term})
    try:
        context = build_context(doc)
        template = settings.LATEX_TEMPLATES[doc.doc_type]
        renderer = LatexRenderer(Path(template), context)
        pdf_bytes = renderer.generate()
        logger.info("PDF generated", extra={"document_id": document_id, "size_bytes": len(pdf_bytes)})
        pdf_url, pdf_path = store_pdf(doc, pdf_bytes)
        doc.pdf_path = pdf_path
        doc.status = "READY"
        doc.completed_at = timezone.now()
        doc.save(update_fields=["pdf_path", "status", "completed_at"])
        duration = (doc.completed_at - doc.created_at).total_seconds() if doc.created_at and doc.completed_at else 0
        mark_ready(doc.id, duration)
        logger.info("PDF stored", extra={"document_id": document_id, "pdf_path": pdf_path, "pdf_url": pdf_url})
        return pdf_url
    except Exception:
        doc.status = "FAILED"
        doc.completed_at = timezone.now()
        doc.save(update_fields=["status", "completed_at"])
        mark_failed(doc.id)
        raise


def _ttl_seconds():
    try:
        return int(getattr(settings, "DOCUMENT_TTL_SECONDS", 300))
    except Exception:
        return 300


@shared_task
def purge_document_file(document_id: int):
    doc = Document.objects.filter(id=document_id).first()
    if not doc or not doc.first_download_at or not doc.pdf_path:
        return
    if timezone.now() - doc.first_download_at < timedelta(seconds=_ttl_seconds()):
        return
    try:
        Path(doc.pdf_path).unlink(missing_ok=True)
        doc.pdf_path = ""
        doc.save(update_fields=["pdf_path"])
        logger.info("Purged PDF after TTL", extra={"document_id": document_id, "path": doc.pdf_path})
    except Exception as exc:
        logger.warning("Failed to purge PDF for doc %s: %s", document_id, exc)


@shared_task
def purge_batch_zip(batch_id: int):
    from documents.models import Batch  # lazy import to avoid cycles

    batch = Batch.objects.filter(id=batch_id).first()
    if not batch or not batch.first_download_at or not batch.zip_path:
        return
    if timezone.now() - batch.first_download_at < timedelta(seconds=_ttl_seconds()):
        return
    try:
        Path(batch.zip_path).unlink(missing_ok=True)
        batch.zip_path = ""
        batch.save(update_fields=["zip_path"])
        logger.info("Purged batch zip after TTL", extra={"batch_id": batch_id, "path": batch.zip_path})
    except Exception as exc:
        logger.warning("Failed to purge batch zip %s: %s", batch_id, exc)


@shared_task
def purge_expired(hours: int = 1):
    cutoff = timezone.now() - timedelta(hours=hours)
    deleted_docs = 0
    for doc in Document.objects.filter(pdf_path__isnull=False).exclude(pdf_path=""):
        ts = doc.first_download_at or doc.completed_at
        if ts and ts < cutoff:
            Path(doc.pdf_path).unlink(missing_ok=True)
            doc.pdf_path = ""
            doc.save(update_fields=["pdf_path"])
            deleted_docs += 1

    from documents.models import Batch

    deleted_batches = 0
    for batch in Batch.objects.filter(zip_path__isnull=False).exclude(zip_path=""):
        ts = batch.first_download_at or batch.completed_at
        if ts and ts < cutoff:
            Path(batch.zip_path).unlink(missing_ok=True)
            batch.zip_path = ""
            batch.save(update_fields=["zip_path"])
            deleted_batches += 1

    logger.info(
        "purge_expired done",
        extra={"hours": hours, "deleted_docs": deleted_docs, "deleted_batches": deleted_batches},
    )
