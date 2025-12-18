from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=64)
    logo = models.ImageField(upload_to="logos/")
    motto = models.CharField(max_length=255, blank=True)
    academic_year = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Class(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    level = models.CharField(max_length=64)
    total_students = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class Student(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    matricule = models.CharField(max_length=64, unique=True)
    klass = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="students")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2)
    teacher_name = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.name} ({self.teacher_name})"


class Grade(models.Model):
    APP_CHOICES = [
        ("INSUFFISANT", "Insuffisant"),
        ("PASSABLE", "Passable"),
        ("BIEN", "Bien"),
        ("EXCELLENT", "Excellent"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    average = models.DecimalField(max_digits=5, decimal_places=2)
    appreciation = models.CharField(max_length=16, choices=APP_CHOICES)

    def __str__(self):
        return f"{self.student} - {self.subject}"


class TermResult(models.Model):
    TERM_CHOICES = [("T1", "T1"), ("T2", "T2"), ("T3", "T3")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.CharField(max_length=2, choices=TERM_CHOICES)
    weighted_total = models.DecimalField(max_digits=7, decimal_places=2)
    average = models.DecimalField(max_digits=4, decimal_places=2)
    rank = models.PositiveIntegerField()
    honor_board = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.term}"

    class Meta:
        indexes = [
            models.Index(fields=["student", "term"], name="termresult_student_term_idx"),
        ]


class FollowUp(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    assiduite = models.PositiveIntegerField()
    ponctualite = models.PositiveIntegerField()
    comportement = models.PositiveIntegerField()
    participation = models.PositiveIntegerField()

    def __str__(self):
        return f"Suivi {self.student}"
