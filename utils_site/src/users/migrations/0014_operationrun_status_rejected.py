from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_update_public_subscription_plans"),
    ]

    operations = [
        migrations.AlterField(
            model_name="operationrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("started", "started"),
                    ("queued", "queued"),
                    ("running", "running"),
                    ("success", "success"),
                    ("error", "error"),
                    ("rejected", "rejected"),
                    ("cancel_requested", "cancel_requested"),
                    ("cancelled", "cancelled"),
                    ("abandoned", "abandoned"),
                ],
                default="started",
                max_length=20,
            ),
        ),
    ]
