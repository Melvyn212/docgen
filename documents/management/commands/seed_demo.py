import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from schools.models import School, Class, Student, Subject, Grade, TermResult, FollowUp


class Command(BaseCommand):
    help = "Peuple la base avec des données de démonstration (3 trimestres). Sans duplication si déjà présent."

    def handle(self, *args, **options):
        with transaction.atomic():
            school, _ = School.objects.get_or_create(
                name="Lycée Horizon Académique",
                defaults={
                    "address": "Avenue des Sciences",
                    "country": "Burkina Faso",
                    "motto": "UNITÉ — PROGRÈS — JUSTICE",
                    "academic_year": "2025-2026",
                },
            )

            klass, _ = Class.objects.get_or_create(
                school=school,
                name="Terminale A",
                defaults={"level": "Terminale", "total_students": 32},
            )

            subjects_data = [
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

            subjects = {}
            for name, coef, teacher in subjects_data:
                subj, _ = Subject.objects.get_or_create(
                    school=school,
                    name=name,
                    defaults={"coefficient": coef, "teacher_name": teacher},
                )
                subjects[name] = subj

            students_data = [
                "Aïssatou Diallo",
                "Souleymane Traoré",
                "Mariam Ouédraogo",
                "Idriss Kaboré",
                "Awa Coulibaly",
                "Dimitri Zongo",
                "Rokia Bationo",
                "Noël Nikiéma",
                "Anissa Sanou",
                "Ismaël Sawadogo",
            ]

            # Moyennes de base par élève pour générer des variations
            base_avgs = [14.8, 13.4, 15.9, 16.5, 12.6, 14.2, 13.1, 15.0, 14.6, 13.8]

            created_students = []
            for idx, full_name in enumerate(students_data, start=1):
                first, last = full_name.split(" ", 1)
                matricule = f"2025-{idx:03d}"
                student, _ = Student.objects.get_or_create(
                    klass=klass,
                    matricule=matricule,
                    defaults={"first_name": first, "last_name": last},
                )
                created_students.append((student, base_avgs[idx - 1]))

            # Crée des notes génériques (Grade sans notion de trimestre)
            for student, base_avg in created_students:
                for subj_name, subj in subjects.items():
                    # variations légères autour de base_avg
                    val = max(8.0, min(19.5, random.gauss(base_avg, 1.2)))
                    Grade.objects.update_or_create(
                        student=student,
                        subject=subj,
                        defaults={
                            "average": Decimal(f"{val:.2f}"),
                            "appreciation": "EXCELLENT" if val >= 16 else ("BIEN" if val >= 14 else "PASSABLE"),
                        },
                    )

                FollowUp.objects.update_or_create(
                    student=student,
                    defaults={
                        "assiduite": random.randint(12, 18),
                        "ponctualite": random.randint(12, 18),
                        "comportement": random.randint(12, 18),
                        "participation": random.randint(12, 18),
                    },
                )

            # TermResults pour T1, T2, T3
            for student, base_avg in created_students:
                for term_code, delta in [("T1", -0.2), ("T2", 0.0), ("T3", 0.1)]:
                    avg_val = max(10.0, min(19.5, base_avg + delta))
                    weighted = avg_val * 30  # approximation pondérée
                    TermResult.objects.update_or_create(
                        student=student,
                        term=term_code,
                        defaults={
                            "weighted_total": Decimal(f"{weighted:.2f}"),
                            "average": Decimal(f"{avg_val:.2f}"),
                            "rank": random.randint(1, klass.total_students),
                            "honor_board": avg_val >= 14.0,
                            "created_at": timezone.now(),
                        },
                    )

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées (3 trimestres)."))
