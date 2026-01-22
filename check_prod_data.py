#!/usr/bin/env python
"""
Script to check OperationRun data retention in production.
Run this via SSH on production server:
  docker compose exec web python /app/check_prod_data.py
"""

import os

import django  # type: ignore

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utils_site.settings")
django.setup()

from datetime import timedelta

from django.conf import settings  # type: ignore
from django.utils import timezone  # type: ignore
from src.users.models import OperationRun, User  # type: ignore

# Check database connection
print("=" * 60)
print("DATABASE CHECK")
print("=" * 60)
db_engine = settings.DATABASES["default"]["ENGINE"]
db_name = settings.DATABASES["default"]["NAME"]
print(f"Database Engine: {db_engine}")
print(f"Database Name: {db_name}")
print()

# Check OperationRun data
print("=" * 60)
print("OPERATIONRUN RECORDS")
print("=" * 60)
total = OperationRun.objects.count()
print(f"Total OperationRun records: {total}")

if total > 0:
    oldest = OperationRun.objects.order_by("created_at").first()
    newest = OperationRun.objects.order_by("-created_at").first()
    print(f"Oldest record: {oldest.created_at} ({oldest.conversion_type})")
    print(f"Newest record: {newest.created_at} ({newest.conversion_type})")

    # Check data by age
    now = timezone.now()
    last_24h = OperationRun.objects.filter(
        created_at__gte=now - timedelta(hours=24)
    ).count()
    last_7d = OperationRun.objects.filter(
        created_at__gte=now - timedelta(days=7)
    ).count()
    last_30d = OperationRun.objects.filter(
        created_at__gte=now - timedelta(days=30)
    ).count()

    print("\nRecords by age:")
    print(f"  Last 24 hours: {last_24h}")
    print(f"  Last 7 days: {last_7d}")
    print(f"  Last 30 days: {last_30d}")

    # Check by status
    print("\nRecords by status:")
    for status, _ in OperationRun.STATUS_CHOICES:
        count = OperationRun.objects.filter(status=status).count()
        if count > 0:
            print(f"  {status}: {count}")
else:
    print("⚠️  NO RECORDS FOUND!")
print()

# Check Users
print("=" * 60)
print("USER RECORDS")
print("=" * 60)
user_count = User.objects.count()
verified_users = User.objects.filter(is_email_verified=True).count()
print(f"Total users: {user_count}")
print(f"Verified users: {verified_users}")
print()

# Check Celery Beat schedule
print("=" * 60)
print("CELERY BEAT SCHEDULE")
print("=" * 60)
if hasattr(settings, "CELERY_BEAT_SCHEDULE"):
    print("Scheduled tasks from settings.py:")
    for task_name, config in settings.CELERY_BEAT_SCHEDULE.items():
        print(f"  - {task_name}: {config.get('task')}")
        if "cleanup" in task_name.lower() or "operation" in task_name.lower():
            print(f"    ⚠️  CLEANUP TASK - Schedule: {config.get('schedule')}s")
            print(f"    ⚠️  Kwargs: {config.get('kwargs', {})}")
else:
    print("No CELERY_BEAT_SCHEDULE found in settings.py")
print()

# Check if celery.py overrides exist
print("=" * 60)
print("CELERY CONFIGURATION CHECK")
print("=" * 60)
try:
    from utils_site import celery as celery_module  # type: ignore

    if hasattr(celery_module, "app") and celery_module.app:
        app = celery_module.app
        if hasattr(app.conf, "beat_schedule"):
            print("⚠️  Celery app has beat_schedule configured in celery.py!")
            schedule = app.conf.beat_schedule
            for task_name, config in schedule.items():
                if "cleanup" in task_name.lower() or "operation" in task_name.lower():
                    print(f"  - {task_name}: {config.get('task')}")
                    print(f"    Schedule: {config.get('schedule')}s")
                    print(f"    Kwargs: {config.get('kwargs', {})}")
        else:
            print("✅ No beat_schedule in celery.py (using settings.py)")
except Exception as e:  # pylint: disable=broad-except
    print(f"Error checking celery.py: {e}")
print()

print("=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)
if total == 0:
    print("❌ NO DATA FOUND - This indicates a problem!")
    print("   Possible causes:")
    print("   1. Data was deleted (check cleanup tasks)")
    print("   2. Database was reset during deploy")
    print("   3. Wrong database is being used")
elif total < 10:
    print("⚠️  VERY FEW RECORDS - Data might be getting deleted")
    print(f"   Only {total} records found - expected more for active site")
else:
    print("✅ Data looks OK")
    print(f"   {total} records found")

print("\nTo prevent data loss:")
print("1. Disable cleanup_old_operations task (or increase retention)")
print("2. Add database backups before deploy")
print("3. Add monitoring for record counts")
