"""
Custom middleware for frontend.
"""

import logging

from django.conf import settings
from django.utils.translation import activate, get_language

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
        if "django_language" not in request.session:
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
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize session variables if needed
        if "captcha_required" not in request.session:
            request.session["captcha_required"] = False
        if "failed_attempts" not in request.session:
            request.session["failed_attempts"] = 0

        response = self.get_response(request)

        # Check if this was a failed request (429 or 400 from spam protection)
        if hasattr(response, "status_code"):
            if response.status_code in [429, 400]:
                # Increment failed attempts
                request.session["failed_attempts"] = (
                    request.session.get("failed_attempts", 0) + 1
                )

                # Require CAPTCHA after 3 failed attempts
                if request.session["failed_attempts"] >= 3:
                    request.session["captcha_required"] = True
                    logger.info(
                        f"CAPTCHA required for IP {request.META.get('REMOTE_ADDR')} after {request.session['failed_attempts']} failed attempts"
                    )
            else:
                # Reset on successful request
                if request.session.get("failed_attempts", 0) > 0:
                    request.session["failed_attempts"] = 0
                    request.session["captcha_required"] = False

        return response
