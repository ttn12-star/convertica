"""Thin Lemon Squeezy REST API wrapper.

Only the methods we actively use are implemented.
LS API docs: https://docs.lemonsqueezy.com/api
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LemonSqueezyError(Exception):
    """Raised on LS API errors."""


class LemonSqueezyClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or settings.LEMONSQUEEZY_API_KEY
        self._base_url = (base_url or settings.LEMONSQUEEZY_API_BASE).rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
                "Authorization": f"Bearer {self._api_key}",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as exc:
            logger.error(
                "Lemon Squeezy transport error",
                extra={"method": method, "path": path, "error": str(exc)[:200]},
            )
            raise LemonSqueezyError(
                f"LS {method} {path} transport error: {exc}"
            ) from exc

        if resp.status_code >= 400:
            logger.error(
                "Lemon Squeezy API error",
                extra={
                    "status": resp.status_code,
                    "body": resp.text[:500],
                    "method": method,
                    "path": path,
                },
            )
            raise LemonSqueezyError(
                f"LS {method} {path} returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code == 204:
            return {}
        return resp.json()

    # --- Checkouts ---

    def create_checkout(
        self,
        *,
        store_id: str,
        variant_id: str,
        custom_data: dict[str, str],
        success_url: str,
        email: str | None = None,
        locale: str = "en",
    ) -> dict[str, str]:
        """POST /v1/checkouts. Returns {id, url}."""
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "custom": custom_data,
                        **({"email": email} if email else {}),
                    },
                    "checkout_options": {
                        "embed": True,
                    },
                    "product_options": {
                        "redirect_url": success_url,
                    },
                    "preview": False,
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": str(store_id)}},
                    "variant": {"data": {"type": "variants", "id": str(variant_id)}},
                },
            }
        }
        body = self._request("POST", "/checkouts", json=payload)
        attrs = body.get("data", {}).get("attributes", {})
        return {
            "id": body.get("data", {}).get("id", ""),
            "url": attrs.get("url", ""),
        }

    # --- Subscriptions ---

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        body = self._request("GET", f"/subscriptions/{subscription_id}")
        data = body.get("data", {})
        return {
            "id": data.get("id"),
            **data.get("attributes", {}),
        }

    def cancel_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/subscriptions/{subscription_id}")

    # --- Customers ---

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        body = self._request("GET", f"/customers/{customer_id}")
        data = body.get("data", {})
        return {
            "id": data.get("id"),
            **data.get("attributes", {}),
        }

    # --- Orders (lifetime, one-time) ---

    def get_order(self, order_id: str) -> dict[str, Any]:
        body = self._request("GET", f"/orders/{order_id}")
        data = body.get("data", {})
        return {
            "id": data.get("id"),
            **data.get("attributes", {}),
        }
