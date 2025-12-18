from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="batch",
            name="first_download_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="first_download_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
