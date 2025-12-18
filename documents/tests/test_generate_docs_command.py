from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from documents.models import Document
from schools.models import Class, School, Student, TermResult


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class GenerateDocsCommandTests(TestCase):
    def setUp(self):
        school = School.objects.create(
            name="Ecole Test",
            address="Adresse",
            country="BF",
            logo="",
            motto="",
            academic_year="2024-2025",
        )
        klass = Class.objects.create(school=school, name="Terminale", level="T", total_students=30)
        self.student1 = Student.objects.create(first_name="A", last_name="Dupont", matricule="M1", klass=klass)
        self.student2 = Student.objects.create(first_name="B", last_name="Durand", matricule="M2", klass=klass)
        TermResult.objects.create(student=self.student1, term="T1", weighted_total=100, average=12, rank=1, honor_board=False)
        TermResult.objects.create(student=self.student2, term="T1", weighted_total=110, average=13, rank=2, honor_board=True)

    @patch("documents.management.commands.generate_docs.generate_document.apply_async")
    def test_reuses_latest_document_and_enqueues(self, mock_apply_async):
        # Deux documents existants pour student1 (duplicata), aucun pour student2
        older = Document.objects.create(student=self.student1, term="T1", doc_type="BULLETIN", status="READY", pdf_path="/old.pdf")
        latest = Document.objects.create(student=self.student1, term="T1", doc_type="BULLETIN", status="READY", pdf_path="/latest.pdf")

        call_command(
            "generate_docs",
            "--type",
            "bulletin",
            "--term",
            "T1",
            "--batch-size",
            "10",
            "--queue",
            "documents_bulk",
        )

        # Pas de nouveau duplicata pour student1, un doc créé pour student2
        self.assertEqual(Document.objects.filter(student=self.student1, term="T1", doc_type="BULLETIN").count(), 2)
        self.assertEqual(Document.objects.filter(student=self.student2, term="T1", doc_type="BULLETIN").count(), 1)

        latest.refresh_from_db()
        self.assertEqual(latest.status, "PENDING")
        self.assertEqual(latest.pdf_path, "")

        # apply_async appelé pour chaque élève
        self.assertEqual(mock_apply_async.call_count, 2)
        for call in mock_apply_async.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(kwargs.get("queue"), "documents_bulk")
