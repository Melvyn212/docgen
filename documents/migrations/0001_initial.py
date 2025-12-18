from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("schools", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(choices=[("T1", "T1"), ("T2", "T2"), ("T3", "T3")], max_length=2)),
                ("doc_type", models.CharField(choices=[("BULLETIN", "Bulletin"), ("HONOR", "HonorBoard")], max_length=10)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("READY", "Ready"), ("FAILED", "Failed")], default="PENDING", max_length=12)),
                ("pdf_path", models.CharField(blank=True, max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="schools.student")),
            ],
        ),
    ]
