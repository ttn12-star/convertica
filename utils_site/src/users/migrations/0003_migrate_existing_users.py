# Migration to migrate existing users from auth.User to users.User

from django.db import migrations


def migrate_users(apps, _schema_editor):
    """Migrate existing users from auth.User to users.User"""
    # Use historical models to avoid AUTH_USER_MODEL conflict
    old_user_model = apps.get_model('auth', 'User')
    new_user_model = apps.get_model('users', 'User')

    # Get all existing users from historical model
    old_users = old_user_model.objects.using('default').all()

    for old_user in old_users:
        # Check if user already exists in new model
        if not new_user_model.objects.filter(email=old_user.email).exists():
            # Create new user with same data
            new_user = new_user_model.objects.create(
                email=old_user.email,
                username=old_user.username,
                first_name=old_user.first_name,
                last_name=old_user.last_name,
                is_staff=old_user.is_staff,
                is_superuser=old_user.is_superuser,
                is_active=old_user.is_active,
                date_joined=old_user.date_joined,
                password=old_user.password,
            )

            # Copy many-to-many relationships
            new_user.groups.set(old_user.groups.all())
            new_user.user_permissions.set(old_user.user_permissions.all())


def reverse_migrate_users(_apps, _schema_editor):
    """Reverse migration - not implemented for safety"""
    # Intentionally left empty - data migration is one-way for safety


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_user_manager"),
    ]

    operations = [
        migrations.RunPython(migrate_users, reverse_migrate_users),
    ]
