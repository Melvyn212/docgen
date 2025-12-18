from django.test import TestCase, override_settings

from documents.models import Document
from documents.services.builder import build_context
from schools.models import Class, Grade, School, Student, Subject, TermResult


@override_settings(LATEX_THEME_FILES={})
class BuilderEscapeTests(TestCase):
    def setUp(self):
        school = School.objects.create(
            name="Ecole #Test",
            address="12 rue_% &Co",
            country="FR",
            logo="",
            motto="Dev#&",
            academic_year="2024-2025",
        )
        klass = Class.objects.create(school=school, name="Term #S", level="T", total_students=25)
        self.student = Student.objects.create(first_name="Jean", last_name="Dupont", matricule="MAT#01", klass=klass)
        subject = Subject.objects.create(school=school, name="Math#1", coefficient=5, teacher_name="Prof_Underscore")
        Grade.objects.create(student=self.student, subject=subject, average=15, appreciation="BIEN")
        TermResult.objects.create(student=self.student, term="T1", weighted_total=200, average=15, rank=1, honor_board=True)

    def test_build_context_escapes_special_chars(self):
        doc = Document(student=self.student, term="T1", doc_type="BULLETIN")
        ctx = build_context(doc)

        # Champs d'en-tête échappés
        self.assertIn(r"Ecole \#Test", ctx["SCHOOL_NAME"])
        self.assertIn(r"12 rue\_\% \&Co", ctx["SCHOOL_ADDRESS"])
        self.assertIn(r"Dev\#\&", ctx["SCHOOL_MOTTO"])
        self.assertIn(r"MAT\#01", ctx["MATRICULE"])

        # Matières échappées dans la table
        self.assertIn(r"Math\#1", ctx["SUBJECT_ROWS"])
        self.assertIn(r"Prof\_Underscore", ctx["SUBJECT_ROWS"])

        # Étudiant échappé
        self.assertIn(r"Jean Dupont", ctx["STUDENT_NAME"])
