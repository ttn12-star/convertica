"""Management command to sync Stripe prices with SubscriptionPlan models."""

import stripe
import stripe.apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from src.users.models import SubscriptionPlan

stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = "Sync Stripe prices with SubscriptionPlan models (create/update stripe_price_id)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created/updated without making changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force recreate prices even if stripe_price_id exists",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - no changes will be made")
            )

        plans = SubscriptionPlan.objects.filter(is_active=True)
        if not plans.exists():
            self.stdout.write(self.style.ERROR("No active subscription plans found"))
            return

        created_count = 0
        skipped_count = 0

        for plan in plans:
            try:
                # Skip if already has stripe_price_id and not forcing
                if plan.stripe_price_id and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {plan.name}: already has stripe_price_id={plan.stripe_price_id}"
                        )
                    )
                    skipped_count += 1
                    continue

                # Create or retrieve Stripe product
                product_id = f"convertica_{plan.slug}"
                try:
                    product = stripe.Product.retrieve(product_id)
                    self.stdout.write(f"Found existing Stripe product: {product.id}")
                except stripe.error.InvalidRequestError:
                    if not dry_run:
                        product = stripe.Product.create(
                            id=product_id,
                            name=plan.name,
                            description=plan.description or f"{plan.name} subscription",
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f"Created Stripe product: {product.id}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[DRY RUN] Would create Stripe product: {product_id}"
                            )
                        )
                        product = None

                # Create Stripe price with idempotency key
                idempotency_key = f"convertica_price_{plan.id}_{int(plan.price * 100)}_{plan.currency}_recurring"

                price_data = {
                    "currency": plan.currency.lower(),
                    "unit_amount": int(plan.price * 100),
                    "recurring": (
                        {"interval": "day", "interval_count": plan.duration_days}
                        if plan.duration_days < 365
                        else {"interval": "year"}
                    ),
                    "product": product.id if product else product_id,
                }

                if not dry_run:
                    price = stripe.Price.create(
                        **price_data, idempotency_key=idempotency_key
                    )

                    with transaction.atomic():
                        plan.stripe_price_id = price.id
                        plan.save(update_fields=["stripe_price_id"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created Stripe price for {plan.name}: {price.id}"
                        )
                    )
                    created_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would create Stripe price for {plan.name} with data: {price_data}"
                        )
                    )
                    created_count += 1

            except stripe.error.StripeError as e:
                self.stdout.write(
                    self.style.ERROR(f"Stripe error for {plan.name}: {e}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {plan.name}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {created_count} prices created/updated, "
                f"{skipped_count} skipped, "
                f"Total active plans: {plans.count()}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis was a DRY RUN. Run without --dry-run to apply changes."
                )
            )
