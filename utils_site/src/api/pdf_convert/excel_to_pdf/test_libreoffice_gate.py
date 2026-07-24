"""Runnable check for the LibreOffice availability gate.

Regression for the false "LibreOffice is not installed or not available in
PATH" that aborted valid Excel->PDF conversions: the old gate spawned
`soffice --version` (10s timeout) which raced the detached soffice.bin
profile lock and timed out under load. The gate now uses shutil.which, so a
missing binary still raises, but a present one is never falsely rejected.

No LibreOffice or network needed (unoserver + which are patched).

Run standalone:  python test_libreoffice_gate.py
Or via pytest:   pytest test_libreoffice_gate.py
"""

import asyncio
from unittest import mock

from src.api.pdf_convert.excel_to_pdf.utils import ExcelToPDFConverter
from src.exceptions import ConversionError


def _run_gate():
    """Drive the subprocess path (unoserver forced off) and return/raise."""
    conv = ExcelToPDFConverter()
    with mock.patch(
        "src.api.unoserver_client.convert_with_unoserver", return_value=False
    ):
        return asyncio.new_event_loop().run_until_complete(
            conv._convert_with_libreoffice_async("/tmp/x.xlsx", "/tmp/x.pdf", {})
        )


def test_missing_binary_raises_path_error():
    with mock.patch("shutil.which", return_value=None):
        try:
            _run_gate()
        except ConversionError as e:
            assert "PATH" in str(e)
        else:
            raise AssertionError("expected ConversionError when which() -> None")


def test_present_binary_passes_gate_without_spawning_version_check():
    # which() finds it -> gate must NOT run any `soffice --version` subprocess.
    # We fail the actual conversion fast (subprocess.run patched to raise) and
    # assert the failure is NOT the availability error: the gate was passed.
    with (
        mock.patch("shutil.which", return_value="/usr/bin/libreoffice"),
        mock.patch("subprocess.run", side_effect=OSError("no real soffice")),
    ):
        try:
            _run_gate()
        except ConversionError as e:
            assert "not installed or not available in PATH" not in str(e)
        else:
            raise AssertionError("expected the conversion (not the gate) to fail")


if __name__ == "__main__":
    test_missing_binary_raises_path_error()
    test_present_binary_passes_gate_without_spawning_version_check()
    print("OK: libreoffice-gate checks passed")
