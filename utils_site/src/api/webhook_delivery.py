"""Deliver async-conversion results to caller-specified URLs."""

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"https"}
DISALLOWED_HOSTNAMES = {"localhost", "metadata.google.internal", "instance-data"}


def _is_safe_url(url: str) -> bool:
    """Block SSRF: private IPs, link-local, metadata endpoints, plain HTTP."""
    try:
        p = urlparse(url)
        if p.scheme not in ALLOWED_SCHEMES:
            return False
        host = (p.hostname or "").lower()
        if not host:
            return False
        if host in DISALLOWED_HOSTNAMES:
            return False
        # Resolve to IPs and reject if any is private/loopback/link-local/multicast/reserved
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False
        for info in infos:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                return False
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return False
        return True
    except Exception as e:
        logger.warning("webhook URL safety check failed for %s: %s", url, e)
        return False


def deliver(*, webhook_url: str, payload: dict, user) -> bool:
    """POST `payload` to `webhook_url`, HMAC-signing the body.

    Returns True on 2xx, False otherwise. Caller decides retry policy.
    """
    if not _is_safe_url(webhook_url):
        logger.warning("webhook rejected (unsafe URL): %s", webhook_url)
        return False
    if not user.webhook_secret:
        logger.warning("webhook delivery skipped — user %s has no secret", user.pk)
        return False
    body = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(user.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    try:
        r = requests.post(
            webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Convertica-Signature": f"sha256={sig}",
                "User-Agent": "convertica-webhook/1.0",
            },
            timeout=10,
        )
        ok = 200 <= r.status_code < 300
        if not ok:
            logger.warning("webhook %s returned %d", webhook_url, r.status_code)
        return ok
    except requests.RequestException as e:
        logger.warning("webhook %s failed: %s", webhook_url, e)
        return False
