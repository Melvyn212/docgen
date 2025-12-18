import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Purge les logs/tex LaTeX archivés (media/latex_logs par défaut)."

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
            help="Chemin du répertoire de logs (défaut: settings.LATEX_LOG_DIR).",
        )

    def handle(self, *args, **options):
        log_dir = Path(options["path"] or getattr(settings, "LATEX_LOG_DIR", settings.MEDIA_ROOT / "latex_logs"))
        days = options["days"]
        max_files = options["max_files"]

        if not log_dir.exists():
            self.stdout.write(self.style.WARNING(f"Répertoire inexistant: {log_dir}"))
            return

        files = sorted([p for p in log_dir.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        deleted = 0

        if max_files is not None and max_files >= 0:
            for p in files[max_files:]:
                p.unlink(missing_ok=True)
                deleted += 1

        if days is not None and days > 0:
            import time

            cutoff = time.time() - days * 86400
            for p in list(log_dir.iterdir()):
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
                    deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Purges effectuées dans {log_dir}. Fichiers supprimés: {deleted}."))
