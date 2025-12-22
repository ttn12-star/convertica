from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone
from src.users.models import User


class Command(BaseCommand):
    help = "Daily update of subscription status and consecutive days"

    def handle(self, *args, **kwargs):
        # Django commands require *args, **kwargs parameters
        # but we don't use them in this specific command
        today = timezone.now().date()
        updated_count = 0

        # Update active subscribers - count real days
        active_users = User.objects.filter(
            is_premium=True, subscription_end_date__gte=today
        )

        for user in active_users:
            if user.subscription_start_date:
                # Calculate real consecutive days
                days_subscribed = (today - user.subscription_start_date.date()).days + 1

                if user.consecutive_subscription_days != days_subscribed:
                    user.consecutive_subscription_days = days_subscribed
                    user.save(update_fields=["consecutive_subscription_days"])
                    updated_count += 1

        # Handle expired subscriptions - reset counters
        expired_users = User.objects.filter(
            is_premium=True, subscription_end_date__lt=today
        )

        for user in expired_users:
            if user.consecutive_subscription_days > 0:
                user.consecutive_subscription_days = 0
                user.is_premium = False
                user.save(update_fields=["consecutive_subscription_days", "is_premium"])
                updated_count += 1

        # Clear cache to refresh heroes lists
        cache.delete("site_heroes")
        cache.delete("top_subscribers_10")

        self.stdout.write(
            self.style.SUCCESS(
                f"Daily update complete: {updated_count} users updated ({len(active_users)} active, {len(expired_users)} expired)"
            )
        )
