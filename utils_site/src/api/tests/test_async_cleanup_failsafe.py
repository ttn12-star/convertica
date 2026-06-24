"""cleanup_async_temp_files must not delete files of a still-running task.

The in-progress guard used to rely solely on a Redis-cache-only flag
(is_task_background); a Redis blip silently returned False and an old-but-running
premium job's dir could be rmtree'd out from under it. The durable backstop is
the OperationRun DB status — an 'running'/'queued'/'started' row pins the dir.
"""

from __future__ import annotations

import os
import time
from unittest import mock

from django.test import TestCase
from src.tasks import maintenance
from src.users.models import OperationRun


class AsyncCleanupFailsafeTests(TestCase):
    def _make_old_task_dir(self, tmp_path, task_id):
        d = os.path.join(tmp_path, task_id)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "input.pdf"), "wb") as fh:
            fh.write(b"x" * 2048)
        old = time.time() - 7200  # 2h, well past the 1h max_age
        os.utime(d, (old, old))
        return d

    def test_running_operationrun_pins_dir_even_if_old(self):
        import tempfile

        root = tempfile.mkdtemp(prefix="async_temp_test_")
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))

        running = self._make_old_task_dir(root, "task-running")
        done = self._make_old_task_dir(root, "task-done")

        OperationRun.objects.create(
            conversion_type="pdf_to_word", task_id="task-running", status="running"
        )
        OperationRun.objects.create(
            conversion_type="pdf_to_word", task_id="task-done", status="success"
        )

        with mock.patch.object(maintenance, "ASYNC_TEMP_DIR", root):
            result = maintenance.cleanup_async_temp_files(max_age_seconds=3600)

        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(running), "running task dir must be preserved")
        self.assertFalse(os.path.exists(done), "finished task dir must be cleaned")
