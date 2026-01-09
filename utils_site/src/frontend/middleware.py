"""
Custom middleware for frontend.
"""

import logging

from django.conf import settings
from django.utils.translation import activate

logger = logging.getLogger(__name__)


class AutoLanguageMiddleware:
    """
    Automatically detect and set user's language preference.
    Only activates if language is not already explicitly set in session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only auto-detect if language is not already in session
        # (i.e., user hasn't explicitly chosen a language)
        # Safely check for session - it may not be available in some edge cases
        if hasattr(request, "session") and "django_language" not in request.session:
            # Try to detect language from Accept-Language header
            accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")

            if accept_language:
                # Parse Accept-Language header
                # Format: "en-US,en;q=0.9,ru;q=0.8"
                languages = []
                for lang_item in accept_language.split(","):
                    lang_item = lang_item.strip()
                    if ";" in lang_item:
                        lang_code = lang_item.split(";")[0].strip()
                    else:
                        lang_code = lang_item.strip()

                    # Extract base language code (e.g., 'en' from 'en-US')
                    base_lang = lang_code.split("-")[0].lower()

                    # Check if this language is supported
                    supported_codes = [code for code, _ in settings.LANGUAGES]
                    if base_lang in supported_codes:
                        languages.append(base_lang)

                # Use first supported language
                if languages:
                    detected_language = languages[0]
                    request.session["django_language"] = detected_language
                    activate(detected_language)
                    logger.debug(f"Auto-detected language: {detected_language}")

        response = self.get_response(request)
        return response


class CaptchaRequirementMiddleware:
    """
    Track failed attempts and require CAPTCHA after multiple failures.

    Uses both session-based (for users with cookies) and IP-based (for cookie-less requests)
    tracking to prevent spam attacks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only track CAPTCHA requirement for API calls.
        # Avoid creating/modifying sessions for anonymous users just browsing pages.
        if not request.path.startswith("/api/"):
            return response

        # Get client IP for IP-based tracking (works even without session)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        # Track failed attempts in session (if available)
        # Note: We track 429 (rate limit) and 400 (spam protection) as failed attempts
        # because excessive requests or spam behavior should trigger CAPTCHA requirement
        if hasattr(request, "session"):
            # Check if this was a failed request (429 or 400 from spam protection)
            if hasattr(response, "status_code"):
                if response.status_code in [429, 400]:
                    # Increment failed attempts in session
                    failed_attempts = request.session.get("failed_attempts", 0) + 1
                    request.session["failed_attempts"] = failed_attempts

                    # Require CAPTCHA after 3 failed attempts (skip in DEBUG mode)
                    if failed_attempts >= 3 and not settings.DEBUG:
                        request.session["captcha_required"] = True
                        logger.info(
                            f"CAPTCHA required for IP {ip} (session-based) after {request.session['failed_attempts']} failed attempts"
                        )
                else:
                    # Reset on successful request (2xx or 3xx status codes)
                    # This allows legitimate users to recover from false positives
                    if request.session.get("failed_attempts", 0) > 0:
                        request.session.pop("failed_attempts", None)
                        request.session.pop("captcha_required", None)

        # Also track failed attempts by IP (for cookie-less spam protection)
        # This provides protection even when sessions are disabled or cookies blocked
        if hasattr(response, "status_code"):
            from django.core.cache import cache

            if response.status_code in [429, 400]:
                # Increment IP-based failed attempts counter
                ip_failed_key = f"captcha_failed_attempts_ip:{ip}"
                ip_captcha_key = f"captcha_required_ip:{ip}"
                try:
                    ip_failed_count = cache.get(ip_failed_key, 0) + 1
                    cache.set(ip_failed_key, ip_failed_count, 3600)  # 1 hour TTL

                    # Require CAPTCHA after 3 failed attempts (same as session-based)
                    if ip_failed_count >= 3 and not settings.DEBUG:
                        cache.set(ip_captcha_key, True, 3600)  # Remember for 1 hour
                        logger.info(
                            f"CAPTCHA required for IP {ip} (IP-based) after {ip_failed_count} failed attempts"
                        )
                except Exception as e:
                    logger.error(
                        f"Error tracking IP-based failed attempts: {str(e)}",
                        exc_info=True,
                    )
            else:
                # Reset IP-based failed attempts counter on successful request
                # Successful request means user is legitimate - allow recovery
                # Note: We only reset failed_attempts counter, not captcha_required flag.
                # The captcha_required flag should only be cleared by explicit CAPTCHA verification
                # in spam_protection.py, or by TTL expiration, to maintain security.
                ip_failed_key = f"captcha_failed_attempts_ip:{ip}"
                try:
                    # Reset failed attempts counter on successful request
                    # This allows legitimate users to recover from false positives
                    if cache.get(ip_failed_key):
                        cache.delete(ip_failed_key)
                except Exception:
                    pass

        return response
