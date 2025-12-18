from pathlib import Path
import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Purge les archives ZIP de batch (media/batches) selon l’âge ou le nombre max."

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
            help="Chemin du répertoire des ZIP (défaut: MEDIA_ROOT/batches).",
        )

    def handle(self, *args, **options):
        batches_dir = Path(options["path"] or (Path(getattr(settings, "MEDIA_ROOT", ".")) / "batches"))
        days = options["days"]
        max_files = options["max_files"]

        if not batches_dir.exists():
            self.stdout.write(self.style.WARNING(f"Répertoire inexistant: {batches_dir}"))
            return

        files = sorted([p for p in batches_dir.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        deleted = 0

        # Si aucun critère n’est fourni, on purge tout
        if days is None and max_files is None:
            for p in files:
                p.unlink(missing_ok=True)
                deleted += 1
        else:
            if max_files is not None and max_files >= 0:
                for p in files[max_files:]:
                    p.unlink(missing_ok=True)
                    deleted += 1

            if days is not None and days > 0:
                cutoff = time.time() - days * 86400
                for p in list(batches_dir.iterdir()):
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        p.unlink(missing_ok=True)
                        deleted += 1

        self.stdout.write(self.style.SUCCESS(f"Purges effectuées dans {batches_dir}. Fichiers supprimés: {deleted}."))
