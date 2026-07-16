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
    help = (
        "Cleanup stuck OperationRun records (queued/running/started/cancel_requested)"
    )

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

        # System failures (never finished) -> abandoned. 'queued' included so a
        # task no worker ever ran doesn't sit 'queued' forever.
        abandoned_ops = OperationRun.objects.filter(
            status__in=["queued", "running", "started"], created_at__lt=cutoff_time
        )
        # User asked to cancel but confirmation never landed -> cancelled.
        cancelled_ops = OperationRun.objects.filter(
            status="cancel_requested", created_at__lt=cutoff_time
        )

        abandoned_count = abandoned_ops.count()
        cancelled_count = cancelled_ops.count()
        count = abandoned_count + cancelled_count

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
                    f"DRY RUN: Would finish {count} operations "
                    f"({abandoned_count} abandoned, {cancelled_count} cancelled):"
                )
            )
            for op in list(abandoned_ops[:10]) + list(cancelled_ops[:10]):
                self.stdout.write(
                    f"  - {op.conversion_type} ({op.status}) - {op.created_at}"
                )
            if count > 20:
                self.stdout.write(f"  ... and {count - 20} more")
        else:
            abandoned_ops.update(
                status="abandoned",
                finished_at=timezone.now(),
                error_type="TimeoutError",
                error_message="Operation abandoned - exceeded maximum processing time",
            )
            cancelled_ops.update(status="cancelled", finished_at=timezone.now())
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully finished {count} operations "
                    f"({abandoned_count} abandoned, {cancelled_count} cancelled)"
                )
            )
