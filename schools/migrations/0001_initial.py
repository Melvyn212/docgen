from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="School",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("address", models.TextField(blank=True)),
                ("country", models.CharField(max_length=64)),
                ("logo", models.ImageField(upload_to="logos/")),
                ("motto", models.CharField(blank=True, max_length=255)),
                ("academic_year", models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name="Class",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("level", models.CharField(max_length=64)),
                ("total_students", models.PositiveIntegerField()),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.school")),
            ],
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=64)),
                ("last_name", models.CharField(max_length=64)),
                ("matricule", models.CharField(max_length=64, unique=True)),
                ("klass", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="students", to="schools.class")),
            ],
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("coefficient", models.DecimalField(decimal_places=2, max_digits=4)),
                ("teacher_name", models.CharField(max_length=128)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.school")),
            ],
        ),
        migrations.CreateModel(
            name="Grade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("average", models.DecimalField(decimal_places=2, max_digits=5)),
                ("appreciation", models.CharField(choices=[("INSUFFISANT", "Insuffisant"), ("PASSABLE", "Passable"), ("BIEN", "Bien"), ("EXCELLENT", "Excellent")], max_length=16)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.student")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.subject")),
            ],
        ),
        migrations.CreateModel(
            name="TermResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(choices=[("T1", "T1"), ("T2", "T2"), ("T3", "T3")], max_length=2)),
                ("weighted_total", models.DecimalField(decimal_places=2, max_digits=7)),
                ("average", models.DecimalField(decimal_places=2, max_digits=4)),
                ("rank", models.PositiveIntegerField()),
                ("honor_board", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.student")),
            ],
        ),
        migrations.CreateModel(
            name="FollowUp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assiduite", models.PositiveIntegerField()),
                ("ponctualite", models.PositiveIntegerField()),
                ("comportement", models.PositiveIntegerField()),
                ("participation", models.PositiveIntegerField()),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.student")),
            ],
        ),
    ]
