from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0023_operationrun_peak_rss_mb"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                blank=True, default="", max_length=10, verbose_name="Preferred Language"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="welcome_email_sent_at",
            field=models.DateTimeField(
                blank=True,
                editable=False,
                null=True,
                verbose_name="Welcome Email Sent At",
            ),
        ),
    ]
