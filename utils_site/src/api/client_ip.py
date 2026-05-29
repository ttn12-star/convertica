"""Shared helper for resolving the trusted client IP behind Cloudflare/nginx.

Centralized so the rate-limiting, spam-protection, admin-whitelist and
web-token paths all agree on which header to trust. The leftmost
``X-Forwarded-For`` entry is client-controlled and must never be used for
security decisions; Cloudflare sets the real client IP in ``CF-Connecting-IP``
and the trusted proxy hop is the rightmost XFF entry.
"""

from __future__ import annotations


def get_client_ip(request) -> str:
    """Return the most trustworthy client IP for the request.

    Order: ``CF-Connecting-IP`` (set by Cloudflare, not client-spoofable) →
    rightmost ``X-Forwarded-For`` entry (the trusted hop) → ``REMOTE_ADDR``.
    """
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf_ip:
        return cf_ip.strip()
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "") or ""
