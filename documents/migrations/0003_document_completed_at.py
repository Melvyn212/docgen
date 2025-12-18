from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_document_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
