"""Tests for the LibreOffice process-group runner (CONVERTICA review B2).

subprocess.run(timeout=...) only kills the direct child on timeout. LibreOffice
forks a detached ``soffice.bin`` that survives, holds the per-conversion profile
lock, and makes later conversions hang. _run_libreoffice launches in a new
session and kills the whole process group on timeout, so detached children die
too.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

from django.test import SimpleTestCase, tag
from src.api.pdf_convert.word_to_pdf_optimized import _run_libreoffice


@tag("slow")  # spawns real subprocesses and asserts a 2.5s wall-clock timeout
class LibreOfficeRunnerTests(SimpleTestCase):
    def test_returns_completed_process_on_success(self):
        result = _run_libreoffice(
            [sys.executable, "-c", "print('ok')"], env=os.environ.copy(), timeout=30
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"ok", result.stdout)

    def test_raises_called_process_error_on_nonzero(self):
        with self.assertRaises(subprocess.CalledProcessError):
            _run_libreoffice(
                [sys.executable, "-c", "import sys; sys.exit(3)"],
                env=os.environ.copy(),
                timeout=30,
            )

    def test_timeout_kills_whole_process_group(self):
        # Parent spawns a detached grandchild that would touch a marker after a
        # delay, then sleeps. On timeout the group must be killed so the marker
        # is never created (proving the grandchild died, not just the parent).
        marker = os.path.join(tempfile.mkdtemp(), "grandchild_ran")
        grandchild = f"import time; time.sleep(2); open({marker!r}, 'w').close()"
        parent = (
            f"import subprocess, sys, time; "
            f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); "
            f"time.sleep(10)"
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_libreoffice(
                [sys.executable, "-c", parent], env=os.environ.copy(), timeout=0.5
            )
        time.sleep(2.5)
        self.assertFalse(
            os.path.exists(marker),
            "grandchild survived timeout — process group was not killed",
        )
