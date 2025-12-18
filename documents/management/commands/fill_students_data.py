import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from schools.models import School, Class, Student, Subject, Grade, TermResult, FollowUp


DEFAULT_SUBJECTS = [
    ("Mathématiques", Decimal("5"), "M. Sawadogo"),
    ("Physique", Decimal("4"), "Mme Ouoba"),
    ("Chimie", Decimal("3"), "M. Kinda"),
    ("SVT", Decimal("3"), "Mme Traoré"),
    ("Français", Decimal("4"), "Mme Compaoré"),
    ("Anglais", Decimal("3"), "M. Barry"),
    ("Histoire-Géo", Decimal("2"), "M. Ouédraogo"),
    ("Philosophie", Decimal("2"), "M. Rouamba"),
    ("Informatique", Decimal("2"), "Mme Zongo"),
    ("EPS", Decimal("1"), "M. Sanou"),
    ("EMC", Decimal("1"), "Mme Kaboré"),
    ("Arts plastiques", Decimal("1"), "Mme Ilboudo"),
]


class Command(BaseCommand):
    help = "Remplit automatiquement tous les champs nécessaires pour chaque élève (subjects, grades, term results T1/T2/T3, follow-up, coordonnées école)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--school",
            type=str,
            help="Nom de l'école à compléter (par défaut toutes).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        school_filter = {}
        if options.get("school"):
            school_filter["name"] = options["school"]

        schools = School.objects.filter(**school_filter)
        if not schools.exists():
            self.stdout.write(self.style.WARNING("Aucune école trouvée."))
            return

        for school in schools:
            self._fill_school(school)

        self.stdout.write(self.style.SUCCESS("Données complètes injectées pour tous les élèves."))  # type: ignore

    def _fill_school(self, school: School):
        # Assure les champs établissement
        if not school.address:
            school.address = "Avenue des Sciences"
        if not school.country:
            school.country = "Burkina Faso"
        if not school.motto:
            school.motto = "UNITÉ — PROGRÈS — JUSTICE"
        if not school.academic_year:
            school.academic_year = "2025-2026"
        school.save()

        # Assure les matières
        subject_map = {}
        for name, coef, teacher in DEFAULT_SUBJECTS:
            subj, _ = Subject.objects.get_or_create(
                school=school,
                name=name,
                defaults={"coefficient": coef, "teacher_name": teacher},
            )
            subject_map[name] = subj

        # Traite les classes de l'école
        for klass in Class.objects.filter(school=school):
            # Total_students à jour
            klass.total_students = klass.students.count() or klass.total_students or 30
            klass.save(update_fields=["total_students"])

            students = Student.objects.filter(klass=klass)
            for student in students:
                self._fill_student(student, subject_map)

    def _fill_student(self, student: Student, subject_map: dict):
        # Notes pour chaque matière
        for subj in subject_map.values():
            grade, created = Grade.objects.get_or_create(
                student=student,
                subject=subj,
                defaults={
                    "average": Decimal(f"{self._random_avg():.2f}"),
                    "appreciation": "BIEN",
                },
            )
            if not created and grade.average is None:
                grade.average = Decimal(f"{self._random_avg():.2f}")
                grade.appreciation = "BIEN"
                grade.save(update_fields=["average", "appreciation"])

        # Suivi
        FollowUp.objects.update_or_create(
            student=student,
            defaults={
                "assiduite": random.randint(12, 18),
                "ponctualite": random.randint(12, 18),
                "comportement": random.randint(12, 18),
                "participation": random.randint(12, 18),
            },
        )

        # Résultats T1, T2, T3
        for term_code in ("T1", "T2", "T3"):
            self._ensure_term_result(student, term_code)

    def _ensure_term_result(self, student: Student, term_code: str):
        grades = Grade.objects.filter(student=student).select_related("subject")
        # calcul moyenne pondérée approximative
        vals, weights = [], []
        for g in grades:
            try:
                a = float(g.average)
                c = float(g.subject.coefficient)
            except Exception:
                continue
            vals.append(a * c)
            weights.append(c)
        avg = sum(vals) / sum(weights) if weights else 12.0
        weighted = avg * 30
        rank = random.randint(1, student.klass.total_students or 30)
        honor = avg >= 14.0
        TermResult.objects.update_or_create(
            student=student,
            term=term_code,
            defaults={
                "average": Decimal(f"{avg:.2f}"),
                "weighted_total": Decimal(f"{weighted:.2f}"),
                "rank": rank,
                "honor_board": honor,
                "created_at": timezone.now(),
            },
        )

    def _random_avg(self) -> float:
        return max(10.0, min(19.0, random.gauss(14.0, 1.8)))
