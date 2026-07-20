"""Runnable check for execute_with_repair_fallback client-error handling.

Client-input errors (e.g. unlocking a PDF that isn't password-protected) must
NOT trigger a repair retry or an error-level log — they are clean 400s, not
Sentry-worthy server faults. Genuine failures must still retry with repair.

Run standalone:  DJANGO_SETTINGS_MODULE=utils_site.settings PYTHONPATH=utils_site \
                 python utils_site/src/api/test_repair_fallback.py
"""

from unittest import mock

from src.api import pdf_utils
from src.api.pdf_utils import execute_with_repair_fallback
from src.exceptions import InvalidPDFError


def test_client_error_not_repaired_or_error_logged():
    calls = []

    def op(path, **kw):
        calls.append(path)
        raise InvalidPDFError("PDF is not password-protected.")

    with (
        mock.patch.object(pdf_utils, "repair_pdf") as repair,
        mock.patch.object(pdf_utils.logger, "error") as err,
    ):
        try:
            execute_with_repair_fallback("/tmp/x.pdf", op)
            raise AssertionError("expected InvalidPDFError to propagate")
        except InvalidPDFError:
            pass

    assert len(calls) == 1, f"client error must not retry; got {len(calls)} calls"
    repair.assert_not_called()  # no wasted repair pass
    err.assert_not_called()  # no Sentry-noise error log


def test_generic_error_still_retries_with_repair():
    calls = []

    def op(path, **kw):
        calls.append(path)
        raise RuntimeError("boom")

    with (
        mock.patch.object(pdf_utils, "repair_pdf", return_value="/tmp/x.pdf") as repair,
        mock.patch.object(pdf_utils.logger, "error"),
    ):
        try:
            execute_with_repair_fallback("/tmp/x.pdf", op)
            raise AssertionError("expected RuntimeError to propagate")
        except RuntimeError:
            pass

    assert len(calls) == 2, "generic failure should retry once after repair"
    repair.assert_called_once()  # repair path intact (no regression)


if __name__ == "__main__":
    test_client_error_not_repaired_or_error_logged()
    test_generic_error_still_retries_with_repair()
    print("OK: repair-fallback client-error checks passed")
