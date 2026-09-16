from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone
from src.users.models import User


class Command(BaseCommand):
    help = "Daily update of subscription status and consecutive days"

    def handle(self, *args, **kwargs):
        # Django commands require *args, **kwargs parameters
        # but we don't use them in this specific command
        now = timezone.now()
        today = now.date()
        # Use timezone-aware datetime for DateTimeField comparisons
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # =====================================================================
        # Update active subscribers - count real days (using bulk_update)
        # =====================================================================
        active_users = list(
            User.objects.filter(
                is_premium=True,
                subscription_end_date__gte=start_of_today,
                subscription_start_date__isnull=False,
            ).only("id", "subscription_start_date", "consecutive_subscription_days")
        )

        users_to_update_active = []
        for user in active_users:
            # Calculate real consecutive days
            days_subscribed = (today - user.subscription_start_date.date()).days + 1

            if user.consecutive_subscription_days != days_subscribed:
                user.consecutive_subscription_days = days_subscribed
                users_to_update_active.append(user)

        # Bulk update active users (single SQL query instead of N queries)
        if users_to_update_active:
            User.objects.bulk_update(
                users_to_update_active,
                ["consecutive_subscription_days"],
                batch_size=500,
            )

        # =====================================================================
        # Handle expired subscriptions - reset counters (using bulk_update)
        # =====================================================================
        expired_users = list(
            User.objects.filter(
                is_premium=True,
                subscription_end_date__lt=start_of_today,
            ).only("id", "consecutive_subscription_days", "is_premium")
        )

        users_to_update_expired = []
        for user in expired_users:
            if user.is_premium:
                # Natural expiry keeps the streak (the user paid for the whole
                # period) — same rule as User.deactivate_premium(reason="expired").
                user.is_premium = False
                users_to_update_expired.append(user)

        # Bulk update expired users (single SQL query instead of N queries)
        if users_to_update_expired:
            User.objects.bulk_update(
                users_to_update_expired,
                ["is_premium"],
                batch_size=500,
            )
            # bulk_update bypasses save(), so the premium caches are not
            # invalidated by the model; do it here.
            from django.core.cache import cache

            cache.delete_many(
                [f"user_premium_active:{u.id}" for u in users_to_update_expired]
                + [f"user_subscription_status_{u.id}" for u in users_to_update_expired]
            )

        # =====================================================================
        # Clear cache to refresh heroes lists
        # =====================================================================
        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")

        # Also clear individual user subscription caches for updated users
        for user in users_to_update_active + users_to_update_expired:
            cache.delete(f"user_subscription_status_{user.id}")

        active_count = len(users_to_update_active)
        expired_count = len(users_to_update_expired)
        total_updated = active_count + expired_count
        self.stdout.write(
            self.style.SUCCESS(
                f"Daily update complete: {total_updated} users updated "
                f"({active_count} active, {expired_count} expired)"
            )
        )
