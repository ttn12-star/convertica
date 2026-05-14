"""Sentry ``before_send`` helpers.

Kept in a standalone module (no Django imports) so they can be unit-tested
without booting the full settings module, and so ``settings.py`` can import
them lazily from inside ``before_send`` without risking import-time side
effects on Django app loading.
"""

# Substrings in pdf2docx page-skip log messages. The library logs these at
# ERROR level via the root logger when a single page fails to render, but
# recovers internally (the page is skipped and conversion continues), so they
# are not actionable bugs — just noise that escalates in Sentry on PDFs with a
# few bad pages.
_PDF2DOCX_PAGE_NOISE_TOKENS = (
    "due to making page error",
    "due to parsing page error",
)


def is_pdf2docx_page_skip_noise(event: dict) -> bool:
    """Return True if event is a pdf2docx page-skip log we want to drop."""
    if event.get("logger") != "root":
        return False
    logentry = event.get("logentry") or {}
    message = str(logentry.get("message") or event.get("message") or "")
    return any(token in message for token in _PDF2DOCX_PAGE_NOISE_TOKENS)
