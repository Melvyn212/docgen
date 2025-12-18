from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="document",
            index=models.Index(fields=["student", "term"], name="document_student_term_idx"),
        ),
    ]
