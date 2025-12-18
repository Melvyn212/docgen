import random

from django.core.management.base import BaseCommand

from schools.models import Class, FollowUp, Grade, School, Student, Subject, TermResult


class Command(BaseCommand):
    help = "Crée des données de démonstration (school, classe, étudiants, matières, notes, résultats) pour tester la génération."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=10, help="Nombre d'étudiants à créer (défaut: 10)")
        parser.add_argument("--term", type=str, default="T1", help="Terme (T1/T2/T3) pour les résultats")
        parser.add_argument("--class-name", type=str, default="Terminale A", help="Nom de la classe à utiliser/créer")
        parser.add_argument("--level", type=str, default="T", help="Niveau de la classe (ex: T, 1ère, 2nde)")

    def handle(self, *args, **options):
        target_students = options["students"]
        term = options["term"]
        class_name = options["class_name"]
        level = options["level"]

        school, _ = School.objects.get_or_create(
            name="Lycée Démo",
            defaults={
                "address": "Rue de la Démo",
                "country": "BF",
                "logo": "",
                "motto": "Excellence et Rigueur",
                "academic_year": "2024-2025",
            },
        )

        klass, _ = Class.objects.get_or_create(
            school=school,
            name=class_name,
            defaults={"level": level, "total_students": target_students},
        )
        klass.total_students = target_students
        klass.save(update_fields=["total_students"])

        subjects_data = [
            ("Mathématiques", 5, "Mme Traoré"),
            ("Physique-Chimie", 4, "M. Ouédraogo"),
            ("SVT", 3, "Mme Kaboré"),
            ("Français", 4, "M. Diallo"),
            ("Anglais", 3, "Mme Zoungrana"),
        ]
        subjects = []
        for name, coef, teacher in subjects_data:
            subj, _ = Subject.objects.get_or_create(
                school=school,
                name=name,
                defaults={"coefficient": coef, "teacher_name": teacher},
            )
            subjects.append(subj)

        first_names = ["Awa", "Ibrahim", "Mariam", "Youssef", "Fatou", "Issa", "Aminata", "Paul", "Claire", "Jean"]
        last_names = ["Traore", "Ouédraogo", "Kaboré", "Zerbo", "Sanogo", "Diallo", "Zongo", "Sawadogo", "Compaoré", "Bationo"]

        created = 0
        for i in range(target_students):
            fn = first_names[i % len(first_names)]
            ln = last_names[(i // len(first_names)) % len(last_names)]
            matricule = f"M{klass.id:02d}{i+1:04d}"
            student, was_created = Student.objects.get_or_create(
                matricule=matricule,
                defaults={"first_name": fn, "last_name": ln, "klass": klass},
            )
            created += 1 if was_created else 0

            # Notes et résultat
            total = 0
            coef_sum = 0
            for subj in subjects:
                avg = random.randint(10, 18)
                Grade.objects.update_or_create(
                    student=student,
                    subject=subj,
                    defaults={"average": avg, "appreciation": "BIEN"},
                )
                total += avg * float(subj.coefficient)
                coef_sum += float(subj.coefficient)
            overall_avg = round(total / coef_sum, 2) if coef_sum else 0
            weighted_total = round(total, 2)
            TermResult.objects.update_or_create(
                student=student,
                term=term,
                defaults={"weighted_total": weighted_total, "average": overall_avg, "rank": i + 1, "honor_board": i < 3},
            )
            FollowUp.objects.update_or_create(
                student=student,
                defaults={"assiduite": 15, "ponctualite": 16, "comportement": 17, "participation": 14},
            )

        self.stdout.write(self.style.SUCCESS(f"École: {school.name}, Classe: {klass.name}, Étudiants créés/nouveaux: {created}/{target_students}"))
