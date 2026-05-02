# Manual E2E checklist (LS test mode)

Before production cutover, walk through this checklist with LS test-mode API
keys and an ngrok tunnel pointing at your local dev stack.

## Setup

1. Run local stack: `make dev` (Django at http://localhost:8000).
2. Run ngrok: `ngrok http 8000` — copy the public URL (e.g. `https://abc.ngrok.io`).
3. In LS Dashboard → Webhooks, add a second webhook endpoint pointing at
   `https://abc.ngrok.io/payments/webhook/lemonsqueezy/`. Copy the signing
   secret into `.env` as `LEMONSQUEEZY_WEBHOOK_SECRET`.
4. Set test-mode API keys in `.env`:
   ```
   LEMONSQUEEZY_API_KEY=test_xxx
   LEMONSQUEEZY_STORE_ID=<your store id>
   LEMONSQUEEZY_WEBHOOK_SECRET=<the secret you set in step 3>
   ```
5. Restart the web container so settings reload.
6. Run `python manage.py create_subscription_plans` and update `ls_variant_id`
   on each plan in admin to match your LS variant IDs (Monthly / Yearly /
   Lifetime products in test mode).

## Scenarios to verify

### 1. Subscribe Monthly (Stripe-equivalent test card)
- [ ] Register a new user, verify email.
- [ ] Visit `/pricing/`, click **Become Monthly Hero**.
- [ ] Card: `4242 4242 4242 4242`, any future expiry, any CVC.
- [ ] Complete checkout in the LS overlay.
- [ ] Browser redirects to `/payments/success/`.
- [ ] In DB: `user.is_premium=True`, `UserSubscription.status="active"`,
      `WebhookEvent.processed_at IS NOT NULL`.
- [ ] Visit `/users/manage-subscription/` → redirected to LS portal URL.

### 2. Subscribe Yearly
- [ ] Same as Monthly but click **Become Yearly Hero**. Period end ~365 days.

### 3. Lifetime purchase
- [ ] Click **Become Lifetime Hero**.
- [ ] After payment: `user.is_premium=True`,
      `user.subscription_end_date IS NULL`, `is_subscription_active()=True`,
      `Payment.amount=129.00`.

### 4. Already-subscribed → portal redirect
- [ ] As a subscribed user, click any Subscribe button on `/pricing/`.
- [ ] JS receives 409 with `portal_url` → browser redirects to LS billing portal.

### 5. Cancel via LS portal
- [ ] In LS portal, cancel the subscription.
- [ ] LS sends `subscription_cancelled` webhook to ngrok.
- [ ] In DB: `UserSubscription.cancel_at_period_end=True`,
      `user.is_premium=True` (still — until period end).

### 6. Resume via LS portal
- [ ] In LS portal, resume the cancelled subscription.
- [ ] In DB: `UserSubscription.cancel_at_period_end=False`, status `active`.

### 7. Refund via LS Dashboard
- [ ] In LS Dashboard, refund the test order.
- [ ] LS sends `subscription_payment_refunded` (or `order_refunded` for Lifetime).
- [ ] In DB: `Payment.status="refunded"`, `user.is_premium=False`.

### 8. Premium-gated tool
- [ ] As free user, attempt to upload 5 files for batch conversion → 403 with
      "Upgrade to Premium" message.
- [ ] After Monthly subscription → 200 (batch processing succeeds).

### 9. Locale
- [ ] Switch site to `/ru/`, click Subscribe → LS overlay should load in
      Russian if LS supports it; English fallback is acceptable.

## Acceptance

All boxes ticked → safe to proceed to Phase 2 (production cutover).
