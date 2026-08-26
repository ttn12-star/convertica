from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0031_add_paddle_price_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="polar_product_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
