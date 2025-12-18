from django.core.management.base import BaseCommand

from documents.services.metrics import reset_metrics


class Command(BaseCommand):
    help = "Réinitialise les métriques Redis utilisées pour le monitoring temps réel."

    def handle(self, *args, **options):
        reset_metrics()
        self.stdout.write(self.style.SUCCESS("Métriques réinitialisées."))
