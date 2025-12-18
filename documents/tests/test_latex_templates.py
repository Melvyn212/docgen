import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings

from documents.models import Document
from documents.services.builder import build_context
from documents.services.latex_renderer import LatexRenderer
from schools.models import Class, Grade, School, Student, Subject, TermResult


class LatexTemplateTests(TestCase):
    def setUp(self):
        school = School.objects.create(
            name="Ecole Étoile",
            address="12 rue des Fleurs",
            country="FR",
            logo="",
            motto="Excellence & Respect",
            academic_year="2024-2025",
        )
        klass = Class.objects.create(school=school, name="Terminale", level="T", total_students=2)
        self.student = Student.objects.create(first_name="Jean", last_name="Martin", matricule="MAT01", klass=klass)
        subject = Subject.objects.create(school=school, name="Mathématiques", coefficient=5, teacher_name="Mme Dupont")
        Grade.objects.create(student=self.student, subject=subject, average=15, appreciation="BIEN")
        TermResult.objects.create(student=self.student, term="T1", weighted_total=200, average=15, rank=1, honor_board=True)

    def _render_tex(self, template_path: Path, doc_type: str, extra_context=None):
        doc = Document(student=self.student, term="T1", doc_type=doc_type)
        ctx = build_context(doc)
        if extra_context:
            ctx.update(extra_context)
        renderer = LatexRenderer(template_path, ctx)
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            tex_path = renderer.render_tex(tmpdir)
            return tex_path.read_text(encoding="utf-8")

    @override_settings(LATEX_THEME_FILES={})
    def test_bulletin_placeholders_replaced(self):
        tex = self._render_tex(
            Path("templates_latex/bulletin.tex"),
            "BULLETIN",
            extra_context={"SCHOOL_PHONE": "0606060606", "SCHOOL_EMAIL": "contact@test.fr"},
        )
        # Aucun placeholder métier ne doit rester
        for token in ("<<SCHOOL_", "<<STUDENT_", "<<CLASS_", "<<TERM_", "<<SUBJECT"):
            self.assertNotIn(token, tex, f"Placeholder {token} not replaced in bulletin")
        # Contacts sur deux lignes
        self.assertIn("FR •", tex)
        self.assertIn("0606060606", tex)
        self.assertIn("contact@test.fr", tex)

    @override_settings(LATEX_THEME_FILES={})
    def test_honor_placeholders_replaced(self):
        tex = self._render_tex(Path("templates_latex/tableau_honneur.tex"), "HONOR")
        for token in ("<<SCHOOL_", "<<STUDENT_", "<<CLASS_", "<<TERM_", "<<HONOR_", "<<AVG"):
            self.assertNotIn(token, tex, f"Placeholder {token} not replaced in honor board")
        self.assertIn("TABLEAU D’HONNEUR", tex)
        self.assertIn("Excellence \\& Respect", tex)

    @override_settings(LATEX_THEME_FILES={})
    def test_honor_ifempty_for_contacts(self):
        # No phone/email provided in theme; ensure no stray bullets
        tex = self._render_tex(Path("templates_latex/tableau_honneur.tex"), "HONOR", extra_context={"SCHOOL_PHONE": "", "SCHOOL_EMAIL": ""})
        self.assertNotIn("•  •", tex)

    @override_settings(LATEX_THEME_FILES={})
    def test_bulletin_watermark_toggle(self):
        tex_on = self._render_tex(Path("templates_latex/bulletin.tex"), "BULLETIN", extra_context={"HAS_WATERMARK": 1})
        tex_off = self._render_tex(Path("templates_latex/bulletin.tex"), "BULLETIN", extra_context={"HAS_WATERMARK": 0})
        self.assertIn("PrintWatermark", tex_on)
        self.assertNotEqual(tex_on, tex_off)
