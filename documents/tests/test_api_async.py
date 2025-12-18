from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from documents.models import Document
from schools.models import Class, Grade, School, Student, Subject, TermResult


class AsyncApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u", password="p")
        school = School.objects.create(
            name="Ecole Test",
            address="Adresse",
            country="BF",
            logo="",
            motto="",
            academic_year="2024-2025",
        )
        klass = Class.objects.create(school=school, name="Terminale", level="T", total_students=30)
        self.student = Student.objects.create(first_name="A", last_name="Dupont", matricule="M1", klass=klass)
        subject = Subject.objects.create(school=school, name="Math", coefficient=5, teacher_name="Mme X")
        Grade.objects.create(student=self.student, subject=subject, average=15, appreciation="BIEN")
        TermResult.objects.create(student=self.student, term="T1", weighted_total=100, average=12, rank=1, honor_board=False)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("documents.api.generate_document.delay")
    def test_reuse_pending_does_not_duplicate_enqueue(self, mock_delay):
        payload = {"student_id": self.student.id, "term": "T1"}
        resp1 = self.client.post("/api/documents/bulletin/", payload, format="json")
        self.assertEqual(resp1.status_code, 202)
        self.assertEqual(Document.objects.count(), 1)
        mock_delay.assert_called_once()

        # Deuxième appel : doc déjà PENDING, pas de nouvel enqueue
        resp2 = self.client.post("/api/documents/bulletin/", payload, format="json")
        self.assertEqual(resp2.status_code, 202)
        self.assertEqual(Document.objects.count(), 1)
        mock_delay.assert_called_once()

    @patch("documents.api.generate_document.delay")
    def test_ready_document_returns_immediately(self, mock_delay):
        ready = Document.objects.create(
            student=self.student,
            term="T1",
            doc_type="BULLETIN",
            status="READY",
            pdf_path="/tmp/x.pdf",
        )
        resp = self.client.post("/api/documents/bulletin/", {"student_id": self.student.id, "term": "T1"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], ready.id)
        self.assertEqual(resp.data["status"], "READY")
        mock_delay.assert_not_called()
