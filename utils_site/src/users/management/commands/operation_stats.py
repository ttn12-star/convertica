"""
Management command to display operation statistics.

Usage:
    python manage.py operation_stats [--days 30] [--export]
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone


class Command(BaseCommand):
    help = "Display operation statistics by type and status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to analyze (default: 30)",
        )
        parser.add_argument(
            "--export",
            action="store_true",
            help="Export statistics to CSV file",
        )

    def handle(self, *args, **options):
        from src.users.models import OperationRun

        days = options["days"]
        export = options["export"]

        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.SUCCESS(f"\n📊 Operation Statistics (Last {days} days)\n")
        )
        self.stdout.write("=" * 80)

        # Overall statistics
        total_ops = OperationRun.objects.filter(created_at__gte=cutoff_date).count()
        successful_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status="success"
        ).count()
        failed_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status="error"
        ).count()
        rejected_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status="rejected"
        ).count()
        pending_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status__in=["started", "queued", "running"]
        ).count()
        cancelled_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status__in=["cancelled", "cancel_requested"]
        ).count()
        abandoned_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, status="abandoned"
        ).count()

        # System success rate ignores 4xx user-input rejects.
        system_attempts = successful_ops + failed_ops
        success_rate = (
            (successful_ops / system_attempts * 100) if system_attempts > 0 else 0
        )

        self.stdout.write("\n📈 Overall Statistics:")
        self.stdout.write(f"   Total Operations: {total_ops}")
        self.stdout.write(f"   Successful: {successful_ops} ({success_rate:.1f}%)")
        self.stdout.write(f"   Failed (5xx): {failed_ops}")
        self.stdout.write(f"   Rejected (4xx): {rejected_ops}")
        self.stdout.write(f"   Pending: {pending_ops}")
        self.stdout.write(f"   Cancelled: {cancelled_ops}")
        self.stdout.write(f"   Abandoned: {abandoned_ops}")

        # Statistics by conversion type
        self.stdout.write("\n📄 By Conversion Type:")
        self.stdout.write("-" * 80)

        type_stats = (
            OperationRun.objects.filter(created_at__gte=cutoff_date)
            .values("conversion_type")
            .annotate(
                total=Count("id"),
                successful=Count("id", filter=Q(status="success")),
                failed=Count("id", filter=Q(status="error")),
                rejected=Count("id", filter=Q(status="rejected")),
                cancelled=Count(
                    "id", filter=Q(status__in=["cancelled", "cancel_requested"])
                ),
                abandoned=Count("id", filter=Q(status="abandoned")),
            )
            .order_by("-total")
        )

        stats_data = []
        for stat in type_stats:
            conv_type = stat["conversion_type"] or "unknown"
            total = stat["total"]
            successful = stat["successful"]
            failed = stat["failed"]
            rejected = stat["rejected"]
            cancelled = stat["cancelled"]
            abandoned = stat["abandoned"]
            attempts = successful + failed
            success_rate = (successful / attempts * 100) if attempts > 0 else 0

            self.stdout.write(
                f"   {conv_type:30} | Total: {total:5} | Success: {successful:5} ({success_rate:5.1f}%) | Failed: {failed:4} | Rejected: {rejected:4} | Cancelled: {cancelled:4} | Abandoned: {abandoned:4}"
            )

            stats_data.append(
                {
                    "conversion_type": conv_type,
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "rejected": rejected,
                    "cancelled": cancelled,
                    "abandoned": abandoned,
                    "success_rate": f"{success_rate:.1f}%",
                }
            )

        # Premium vs Free
        self.stdout.write("\n💎 Premium vs Free:")
        self.stdout.write("-" * 80)

        premium_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, is_premium=True
        ).count()
        free_ops = OperationRun.objects.filter(
            created_at__gte=cutoff_date, is_premium=False
        ).count()

        self.stdout.write(f"   Premium Operations: {premium_ops}")
        self.stdout.write(f"   Free Operations: {free_ops}")

        # Export to CSV if requested
        if export:
            import csv
            from pathlib import Path

            export_dir = Path("/app/logs/operation_stats")
            export_dir.mkdir(parents=True, exist_ok=True)

            export_file = (
                export_dir
                / f"operation_stats_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            with open(export_file, "w", newline="") as csvfile:
                fieldnames = [
                    "conversion_type",
                    "total",
                    "successful",
                    "failed",
                    "rejected",
                    "cancelled",
                    "abandoned",
                    "success_rate",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in stats_data:
                    writer.writerow(row)

            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Statistics exported to: {export_file}")
            )

        self.stdout.write("\n" + "=" * 80 + "\n")
