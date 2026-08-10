"""Thin Paddle Billing REST API wrapper.

Only the calls we actually make are implemented. Notably absent is checkout
creation: Paddle.js opens the overlay client-side from a price id, so there is
no server round-trip to create one (unlike Lemon Squeezy).

API docs: https://developer.paddle.com/api-reference/overview
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaddleError(Exception):
    """Raised on Paddle API errors."""


class PaddleClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or settings.PADDLE_API_KEY
        self._base_url = (base_url or settings.PADDLE_API_BASE).rstrip("/")
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
                "Paddle transport error",
                extra={"method": method, "path": path, "error": str(exc)[:200]},
            )
            raise PaddleError(f"Paddle {method} {path} transport error: {exc}") from exc

        if resp.status_code >= 400:
            logger.error(
                "Paddle API error",
                extra={
                    "status": resp.status_code,
                    "body": resp.text[:500],
                    "method": method,
                    "path": path,
                },
            )
            raise PaddleError(
                f"Paddle {method} {path} returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # --- Subscriptions ---

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self._request("GET", f"/subscriptions/{subscription_id}").get("data", {})

    def cancel_subscription(
        self, subscription_id: str, *, immediately: bool = False
    ) -> dict[str, Any]:
        """Schedule a cancellation.

        Default is end-of-period: the customer paid through the current cycle
        and keeps access until it runs out, which is what our refund policy
        promises. `immediately` is for refunds, where access must stop now.
        """
        payload = {
            "effective_from": "immediately" if immediately else "next_billing_period"
        }
        body = self._request(
            "POST", f"/subscriptions/{subscription_id}/cancel", json=payload
        )
        return body.get("data", {})

    # --- Customer portal ---

    def create_portal_session(
        self, customer_id: str, subscription_ids: list[str] | None = None
    ) -> dict[str, str]:
        """Create a customer portal session and return its urls.

        Paddle portal links are short-lived and must be minted per visit, so
        this is called on demand rather than stored.
        """
        payload = {"subscription_ids": subscription_ids or []}
        data = self._request(
            "POST", f"/customers/{customer_id}/portal-sessions", json=payload
        ).get("data", {})
        urls = data.get("urls", {}) or {}
        general = urls.get("general", {}) or {}
        subs = urls.get("subscriptions", []) or []
        return {
            "overview": general.get("overview", ""),
            # Deep link straight to the subscription when Paddle gives us one —
            # it skips a click and lands the customer where they meant to go.
            "cancel": (subs[0].get("cancel_subscription", "") if subs else ""),
            "update_payment_method": (
                subs[0].get("update_subscription_payment_method", "") if subs else ""
            ),
        }

    # --- Customers ---

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        return self._request("GET", f"/customers/{customer_id}").get("data", {})
