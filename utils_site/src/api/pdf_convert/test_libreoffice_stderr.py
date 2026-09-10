"""Runnable check: a failed LibreOffice run must not crash the error handler.

Regression for the 500s on /api/excel-to-pdf/ (Sentry 146080285, 10.09.2026):
LibreOffice was OOM-killed (exit 137), and the handler called
`e.stderr.decode()` on stderr that `subprocess.run(text=True)` had already
decoded to str -> AttributeError, so a handled conversion failure surfaced as
an Internal Server Error. Same handler exists in the ppt converter.

No LibreOffice needed (which + subprocess.run are patched).

Run standalone:  python test_libreoffice_stderr.py
Or via pytest:   pytest test_libreoffice_stderr.py
"""

import asyncio
import subprocess
from unittest import mock

from src.api.pdf_convert.excel_to_pdf.utils import ExcelToPDFConverter
from src.api.pdf_convert.ppt_to_pdf.utils import PowerPointToPDFConverter
from src.exceptions import ConversionError


def _run(converter, returncode, stderr):
    """Drive the subprocess path with LibreOffice failing as it does in prod.

    Leaves the number of LibreOffice attempts in `_run.calls`.
    """
    err = subprocess.CalledProcessError(returncode, ["libreoffice"], stderr=stderr)
    with (
        mock.patch(
            "src.api.unoserver_client.convert_with_unoserver", return_value=False
        ),
        mock.patch("shutil.which", return_value="/usr/bin/libreoffice"),
        mock.patch("subprocess.run", side_effect=err) as run,
    ):
        try:
            asyncio.new_event_loop().run_until_complete(
                converter._convert_with_libreoffice_async("/tmp/x.in", "/tmp/x.pdf", {})
            )
        finally:
            _run.calls = run.call_count


def test_str_stderr_raises_conversion_error_not_attribute_error():
    for converter in (ExcelToPDFConverter(), PowerPointToPDFConverter()):
        try:
            _run(converter, 1, "soffice exploded\n")
        except ConversionError as e:
            assert "soffice exploded" in str(e), str(e)
            assert _run.calls == 3, f"a transient failure got {_run.calls} attempts"
        else:
            raise AssertionError(f"expected ConversionError from {converter}")


def test_oom_kill_says_the_file_was_too_big_and_is_not_retried():
    # exit 137 leaves only the useless javaldx warning in stderr, and retrying
    # an OOM kill only buys two more OOM kills.
    try:
        _run(
            ExcelToPDFConverter(),
            137,
            "Warning: failed to launch javaldx - java may not function correctly\n",
        )
    except ConversionError as e:
        assert "too large or complex" in str(e), str(e)
        assert _run.calls == 1, f"OOM was retried {_run.calls} times"
    else:
        raise AssertionError("expected ConversionError on exit 137")


if __name__ == "__main__":
    test_str_stderr_raises_conversion_error_not_attribute_error()
    test_oom_kill_says_the_file_was_too_big_and_is_not_retried()
    print("ok")
