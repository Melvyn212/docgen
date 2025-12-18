from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Purge les PDFs générés en local (DOCUMENT_STORAGE_PATH). Utile si stockage S3 activé."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Supprimer les fichiers modifiés il y a plus de N jours.",
        )
        parser.add_argument(
            "--max-files",
            type=int,
            default=None,
            help="Garder seulement les N fichiers les plus récents, supprimer le reste.",
        )
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Chemin du répertoire de PDFs (défaut: settings.DOCUMENT_STORAGE_PATH).",
        )

    def handle(self, *args, **options):
        pdf_dir = Path(options["path"] or getattr(settings, "DOCUMENT_STORAGE_PATH", settings.MEDIA_ROOT / "documents"))
        days = options["days"]
        max_files = options["max_files"]

        if not pdf_dir.exists():
            self.stdout.write(self.style.WARNING(f"Répertoire inexistant: {pdf_dir}"))
            return

        files = sorted([p for p in pdf_dir.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        deleted = 0

        # Si aucun critère n'est fourni, on purge tout
        if max_files is None and days is None:
            for p in files:
                p.unlink(missing_ok=True)
                deleted += 1
        else:
            if max_files is not None and max_files >= 0:
                for p in files[max_files:]:
                    p.unlink(missing_ok=True)
                    deleted += 1

            if days is not None and days > 0:
                import time

                cutoff = time.time() - days * 86400
                for p in list(pdf_dir.iterdir()):
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        p.unlink(missing_ok=True)
                        deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Purges effectuées dans {pdf_dir}. Fichiers supprimés: {deleted}."))
