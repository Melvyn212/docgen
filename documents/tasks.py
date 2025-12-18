from pathlib import Path
import logging

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
