"""Thin Polar REST API wrapper.

Only the calls we actually make are implemented. Unlike Paddle (overlay opened
client-side from a price id) Polar mints a hosted checkout server-side and hands
back a URL, so this is shaped like the Lemon Squeezy client and the front-end
needs no provider-specific branch: it just follows `checkout_url`.

Request/response shapes below were verified against the live sandbox API on
2026-08-26 rather than taken from the docs, which 404 on several paths.

API docs: https://polar.sh/docs/api-reference
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PolarError(Exception):
    """Raised on Polar API errors."""


class PolarClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or settings.POLAR_ACCESS_TOKEN
        self._base_url = (base_url or settings.POLAR_API_BASE).rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as exc:
            logger.error(
                "Polar transport error",
                extra={"method": method, "path": path, "error": str(exc)[:200]},
            )
            raise PolarError(f"Polar {method} {path} transport error: {exc}") from exc

        if resp.status_code >= 400:
            logger.error(
                "Polar API error",
                extra={
                    "status": resp.status_code,
                    "body": resp.text[:500],
                    "method": method,
                    "path": path,
                },
            )
            raise PolarError(
                f"Polar {method} {path} returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # --- Checkout ---

    def create_checkout(
        self,
        *,
        product_id: str,
        success_url: str,
        email: str = "",
        metadata: dict[str, str] | None = None,
        external_customer_id: str = "",
        customer_metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Create a hosted checkout and return its id and URL.

        Attribution is deliberately belt-and-braces. Polar only documents
        checkout `metadata` being copied onto the subscription for the
        upgrade-an-existing-subscription flow, so a fresh checkout also stamps
        `external_customer_id` (our user id, which Polar carries on the customer
        it creates) and `customer_metadata`. The webhook reads whichever of the
        three arrived; losing all of them would orphan a real payment.
        """
        payload: dict[str, Any] = {
            "products": [product_id],
            "success_url": success_url,
        }
        if email:
            payload["customer_email"] = email
        if metadata:
            payload["metadata"] = metadata
        if external_customer_id:
            payload["external_customer_id"] = external_customer_id
        if customer_metadata:
            payload["customer_metadata"] = customer_metadata
        data = self._request("POST", "/v1/checkouts/", json=payload)
        return {"id": data.get("id", ""), "url": data.get("url", "")}

    # --- Subscriptions ---

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/subscriptions/{subscription_id}")

    def cancel_subscription(
        self, subscription_id: str, *, immediately: bool = False
    ) -> dict[str, Any]:
        """Schedule a cancellation.

        Default is end-of-period: the customer paid through the current cycle
        and keeps access until it runs out, which is what our refund policy
        promises. `immediately` is for refunds, where access must stop now.

        Polar splits these into two distinct request bodies on the same PATCH
        (`SubscriptionCancel` vs `SubscriptionRevoke`); sending both at once is
        rejected.
        """
        payload = {"revoke": True} if immediately else {"cancel_at_period_end": True}
        return self._request(
            "PATCH", f"/v1/subscriptions/{subscription_id}", json=payload
        )

    # --- Customer portal ---

    def create_portal_url(self, customer_id: str) -> str:
        """Mint a customer portal session and return its URL.

        Sessions are short-lived, so this is called on demand rather than
        stored, same as the Paddle portal.
        """
        data = self._request(
            "POST", "/v1/customer-sessions/", json={"customer_id": customer_id}
        )
        return data.get("customer_portal_url", "") or ""
