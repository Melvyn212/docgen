from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="termresult",
            index=models.Index(fields=["student", "term"], name="termresult_student_term_idx"),
        ),
    ]
