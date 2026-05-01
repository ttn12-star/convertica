"""Sample webhook payloads from LS docs.

We use representative fixtures rather than full LS bodies — enough to drive
business logic. Refer to https://docs.lemonsqueezy.com/help/webhooks for the
exact shape.
"""


def subscription_created_payload(
    *,
    user_id,
    plan_id,
    sub_id="sub_1",
    customer_id="cust_1",
    variant_id="var_1",
    ends_at=None
):
    return {
        "meta": {
            "event_name": "subscription_created",
            "test_mode": True,
            "custom_data": {"user_id": str(user_id), "plan_id": str(plan_id)},
        },
        "data": {
            "type": "subscriptions",
            "id": sub_id,
            "attributes": {
                "store_id": 1,
                "customer_id": customer_id,
                "order_id": "ord_1",
                "variant_id": variant_id,
                "user_email": "u@t.test",
                "status": "active",
                "cancelled": False,
                "renews_at": ends_at or "2026-06-01T00:00:00.000000Z",
                "ends_at": None,
                "trial_ends_at": None,
                "created_at": "2026-05-01T00:00:00.000000Z",
            },
        },
    }


def subscription_updated_payload(
    *,
    user_id,
    plan_id,
    status="active",
    cancelled=False,
    sub_id="sub_1",
    customer_id="cust_1",
    variant_id="var_1",
    renews_at="2026-07-01T00:00:00.000000Z",
    ends_at=None
):
    return {
        "meta": {
            "event_name": "subscription_updated",
            "test_mode": True,
            "custom_data": {"user_id": str(user_id), "plan_id": str(plan_id)},
        },
        "data": {
            "type": "subscriptions",
            "id": sub_id,
            "attributes": {
                "store_id": 1,
                "customer_id": customer_id,
                "variant_id": variant_id,
                "status": status,
                "cancelled": cancelled,
                "renews_at": renews_at,
                "ends_at": ends_at,
            },
        },
    }


def subscription_cancelled_payload(**kw):
    p = subscription_updated_payload(status="cancelled", cancelled=True, **kw)
    p["meta"]["event_name"] = "subscription_cancelled"
    return p


def subscription_expired_payload(**kw):
    p = subscription_updated_payload(status="expired", cancelled=True, **kw)
    p["meta"]["event_name"] = "subscription_expired"
    return p


def subscription_payment_success_payload(
    *,
    user_id,
    plan_id,
    sub_id="sub_1",
    customer_id="cust_1",
    order_id="ord_42",
    amount_cents=799
):
    return {
        "meta": {
            "event_name": "subscription_payment_success",
            "test_mode": True,
            "custom_data": {"user_id": str(user_id), "plan_id": str(plan_id)},
        },
        "data": {
            "type": "subscription-invoices",
            "id": "inv_1",
            "attributes": {
                "subscription_id": sub_id,
                "customer_id": customer_id,
                "order_id": order_id,
                "total": amount_cents,
                "status": "paid",
                "billing_reason": "renewal",
            },
        },
    }


def subscription_payment_failed_payload(**kw):
    p = subscription_payment_success_payload(**kw)
    p["meta"]["event_name"] = "subscription_payment_failed"
    p["data"]["attributes"]["status"] = "failed"
    return p


def subscription_payment_refunded_payload(**kw):
    p = subscription_payment_success_payload(**kw)
    p["meta"]["event_name"] = "subscription_payment_refunded"
    p["data"]["attributes"]["status"] = "refunded"
    return p


def order_created_payload(
    *,
    user_id,
    plan_id,
    order_id="ord_lifetime_1",
    customer_id="cust_2",
    variant_id="var_lifetime",
    amount_cents=12900
):
    return {
        "meta": {
            "event_name": "order_created",
            "test_mode": True,
            "custom_data": {"user_id": str(user_id), "plan_id": str(plan_id)},
        },
        "data": {
            "type": "orders",
            "id": order_id,
            "attributes": {
                "customer_id": customer_id,
                "first_order_item": {"variant_id": variant_id},
                "total": amount_cents,
                "status": "paid",
                "refunded": False,
            },
        },
    }


def order_refunded_payload(**kw):
    p = order_created_payload(**kw)
    p["meta"]["event_name"] = "order_refunded"
    p["data"]["attributes"]["refunded"] = True
    return p
