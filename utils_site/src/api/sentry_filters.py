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


def is_celery_hard_timeout_cascade(event: dict, hint: dict) -> bool:
    """Return True if event belongs to the Celery hard-timeout cascade.

    When a Celery task exceeds its hard time limit, three separate events
    surface in Sentry from three different loggers describing the *same*
    enforced shutdown:

    1. ``billiard.exceptions.TimeLimitExceeded`` exception — Celery's own
       signal that the worker terminated the task. Handled by Celery's
       request layer; it's not an unhandled exception in our code.
    2. ``celery.worker.request`` ERROR log: "Hard time limit (Ns)
       exceeded for <task>[...]" — the same enforcement, logged.
    3. ``multiprocessing`` ERROR log: "Process 'ForkPoolWorker-N' pid:M
       exited with 'signal 9 (SIGKILL)'" — billiard SIGKILL'ing the
       worker pid that ran the timed-out task.

    Together these triple every Celery hard-timeout occurrence into three
    Sentry issues. They are operational signals, not bugs — drop them so
    real exceptions stay visible.

    Bare SIGKILL events from ``multiprocessing`` that *aren't* the
    ForkPoolWorker pattern are kept on purpose: they may indicate the
    OOM killer or an external crash worth investigating.
    """
    # 1) The exception itself, captured via Celery's request handler.
    exc_info = hint.get("exc_info") if hint else None
    if exc_info:
        exc_type = exc_info[0]
        if exc_type and exc_type.__name__ == "TimeLimitExceeded":
            return True

    logger_name = event.get("logger") or ""
    logentry = event.get("logentry") or {}
    message = str(logentry.get("message") or event.get("message") or "")
    params = logentry.get("params") or []
    full_message = message + " " + " ".join(str(p) for p in params)

    # 2) Celery's own log line about the enforcement.
    if logger_name == "celery.worker.request" and "Hard time limit" in full_message:
        return True

    # 3) billiard SIGKILL'ing the ForkPoolWorker that ran the task.
    return (
        logger_name == "multiprocessing"
        and "ForkPoolWorker" in full_message
        and ("signal 9" in full_message or "SIGKILL" in full_message)
    )
