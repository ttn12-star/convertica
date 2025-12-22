# Generated migration for composite indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_operationrun'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='operationrun',
            index=models.Index(fields=['user', 'status', '-created_at'], name='users_opera_user_id_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='operationrun',
            index=models.Index(fields=['is_premium', 'status', '-created_at'], name='users_opera_is_prem_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='operationrun',
            index=models.Index(fields=['conversion_type', 'status', '-created_at'], name='users_opera_conv_ty_status_created_idx'),
        ),
    ]
