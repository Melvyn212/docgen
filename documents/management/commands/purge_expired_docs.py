from pathlib import Path
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from documents.models import Document, Batch


class Command(BaseCommand):
    help = "Purge les PDFs et ZIP dont le completed_at/first_download_at dépasse un âge (par défaut 1h)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=1,
            help="Supprimer les fichiers complétés/téléchargés il y a plus de N heures (défaut: 1h).",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        cutoff = timezone.now() - timedelta(hours=hours)

        deleted_docs = 0
        for doc in Document.objects.filter(pdf_path__isnull=False).exclude(pdf_path=""):
            ts = doc.first_download_at or doc.completed_at
            if ts and ts < cutoff:
                Path(doc.pdf_path).unlink(missing_ok=True)
                doc.pdf_path = ""
                doc.save(update_fields=["pdf_path"])
                deleted_docs += 1

        deleted_batches = 0
        for batch in Batch.objects.filter(zip_path__isnull=False).exclude(zip_path=""):
            ts = batch.first_download_at or batch.completed_at
            if ts and ts < cutoff:
                Path(batch.zip_path).unlink(missing_ok=True)
                batch.zip_path = ""
                batch.save(update_fields=["zip_path"])
                deleted_batches += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Purge terminée (> {hours}h) — PDFs supprimés: {deleted_docs}, ZIP supprimés: {deleted_batches}"
            )
        )
