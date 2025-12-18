import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from documents.models import Document
from documents.tasks import generate_document
from documents.services.metrics import mark_pending
from schools.models import Student


class Command(BaseCommand):
    help = "Enqueue bulk generation of documents (bulletins / tableaux d'honneur) for many students."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            dest="doc_type",
            required=True,
            choices=["bulletin", "honor"],
            help="Type de document à générer (bulletin ou honor).",
        )
        parser.add_argument(
            "--term",
            dest="term",
            required=True,
            help="Terme (ex: T1, T2, T3).",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=500,
            help="Taille des lots pour l'enqueue (défaut: 500).",
        )
        parser.add_argument(
            "--queue",
            dest="queue",
            default="documents",
            help="Nom de la file Celery à utiliser (défaut: documents).",
        )
        parser.add_argument(
            "--student-ids",
            nargs="+",
            type=int,
            dest="student_ids",
            help="Liste d'IDs d'élèves à traiter (sinon tous les élèves).",
        )

    def handle(self, *args, **options):
        doc_type = options["doc_type"].upper()
        term = options["term"]
        batch_size = options["batch_size"]
        queue = options["queue"]
        student_ids = options.get("student_ids")

        if doc_type not in dict(Document.DOC_TYPES):
            raise CommandError(f"Type inconnu: {doc_type}. Choisir parmi: bulletin, honor.")

        students_qs = Student.objects.all()
        if student_ids:
            students_qs = students_qs.filter(id__in=student_ids)

        total = students_qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Aucun élève trouvé."))
            return

        self.stdout.write(f"Enqueue {total} documents ({doc_type}, {term}) par lots de {batch_size} sur la queue '{queue}'")

        created = 0
        enqueued = 0

        for offset in range(0, total, batch_size):
            batch = list(students_qs.order_by("id")[offset : offset + batch_size])
            to_enqueue = []
            with transaction.atomic():
                for student in batch:
                    existing_qs = Document.objects.filter(student=student, term=term, doc_type=doc_type).order_by("-created_at")
                    if existing_qs.exists():
                        doc = existing_qs.first()
                        prev_status = doc.status
                        if existing_qs.count() > 1:
                            logging.getLogger(__name__).warning(
                                "Multiple documents found, using latest",
                                extra={
                                    "student": student.id,
                                    "term": term,
                                    "doc_type": doc_type,
                                    "count": existing_qs.count(),
                                },
                            )
                        doc.status = "PENDING"
                        doc.pdf_path = ""
                        doc.completed_at = None
                        doc.save(update_fields=["status", "pdf_path", "completed_at"])
                        if prev_status != "PENDING":
                            mark_pending(doc.id)
                    else:
                        doc = Document.objects.create(
                            student=student,
                            term=term,
                            doc_type=doc_type,
                            status="PENDING",
                            pdf_path="",
                            completed_at=None,
                        )
                        mark_pending(doc.id)
                        created += 1
                    to_enqueue.append(doc.id)
            for doc_id in to_enqueue:
                generate_document.apply_async(args=[doc_id], queue=queue)
                enqueued += 1
            self.stdout.write(f"Lot {offset//batch_size + 1}: {len(batch)} élèves traités, {enqueued} tâches en file.")

        self.stdout.write(self.style.SUCCESS(f"Terminé. Documents créés/réinitialisés: {created}. Tâches enqueued: {enqueued}."))
