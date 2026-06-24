"""Tests for the system /tmp sweep maintenance task.

Converters mkdtemp() working dirs in the system temp dir; a SIGKILL/OOM mid-job
(or a converter that makes several temp dirs) leaks them. cleanup_system_tmp is
the backstop that keeps /tmp from filling and taking all conversions down with
ENOSPC — so it must remove OLD entries that match a known converter prefix while
never touching recent ones (a still-running job) or unrelated entries.
"""

from __future__ import annotations

import os
import tempfile
import time

from django.test import SimpleTestCase
from src.tasks.maintenance import cleanup_system_tmp


class CleanupSystemTmpTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.gettempdir()
        self.created = []

    def tearDown(self):
        import shutil

        for p in self.created:
            shutil.rmtree(p, ignore_errors=True)
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def _mkdir(self, prefix, age_seconds):
        d = tempfile.mkdtemp(prefix=prefix)
        self.created.append(d)
        # drop a file inside so it's a realistic working dir
        with open(os.path.join(d, "work.bin"), "wb") as fh:
            fh.write(b"x" * 1024)
        old = time.time() - age_seconds
        os.utime(d, (old, old))
        return d

    def test_removes_old_converter_dir_keeps_fresh_and_unrelated(self):
        old_conv = self._mkdir("pdf2jpg_", age_seconds=7200)  # 2h, converter prefix
        fresh_conv = self._mkdir("pdf2jpg_", age_seconds=60)  # 1m, still "running"
        unrelated = self._mkdir("totally_unrelated_", age_seconds=7200)  # not a prefix

        result = cleanup_system_tmp(max_age_seconds=3600)

        self.assertEqual(result["status"], "success")
        self.assertFalse(os.path.exists(old_conv), "old converter dir must be swept")
        self.assertTrue(os.path.exists(fresh_conv), "recent job dir must be kept")
        self.assertTrue(os.path.exists(unrelated), "non-converter dir must be kept")
        self.assertGreaterEqual(result["cleaned"], 1)
