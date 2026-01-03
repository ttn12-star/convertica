"""
Management command to cleanup stuck OperationRun records.

Usage:
    python manage.py cleanup_stuck_operations
    python manage.py cleanup_stuck_operations --hours 24
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from src.users.models import OperationRun


class Command(BaseCommand):
    help = "Cleanup stuck OperationRun records (running/started status)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=1,
            help="Maximum age in hours before marking as abandoned (default: 1)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be cleaned without actually cleaning",
        )

    def handle(self, *args, **options):
        max_age_hours = options["hours"]
        dry_run = options["dry_run"]

        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

        stuck_operations = OperationRun.objects.filter(
            status__in=["running", "started"], created_at__lt=cutoff_time
        )

        count = stuck_operations.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No stuck operations found (older than {max_age_hours} hours)"
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would mark {count} operations as abandoned:"
                )
            )
            for op in stuck_operations[:10]:
                self.stdout.write(
                    f"  - {op.conversion_type} ({op.status}) - {op.created_at}"
                )
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
        else:
            stuck_operations.update(
                status="abandoned",
                finished_at=timezone.now(),
                error_type="TimeoutError",
                error_message="Operation abandoned - exceeded maximum processing time",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully marked {count} operations as abandoned"
                )
            )
