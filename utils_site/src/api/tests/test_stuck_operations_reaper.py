"""Tests for the stuck-operation reaper window (CONVERTICA review B3).

After an OOM SIGKILL (worker_max_memory_per_child) none of the task's
except/finally blocks run, so its OperationRun stays 'running' forever. The
reaper used a 24h window, leaving a hung row (and a spinning progress bar) for
a full day. The conversion hard time limit is 8 minutes, so anything still
'running' after ~1h is definitively stuck.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from src.tasks.maintenance import cleanup_stuck_operations
from src.users.models import OperationRun


class StuckOperationReaperTests(TestCase):
    def _make(self, status, created_minutes_ago):
        op = OperationRun.objects.create(conversion_type="pdf_to_word", status=status)
        # created_at is auto_now_add; override via queryset update to backdate.
        OperationRun.objects.filter(pk=op.pk).update(
            created_at=timezone.now() - timedelta(minutes=created_minutes_ago)
        )
        op.refresh_from_db()
        return op

    def test_reaps_running_op_older_than_window(self):
        op = self._make("running", created_minutes_ago=90)
        cleanup_stuck_operations(max_age_minutes=60)
        op.refresh_from_db()
        self.assertEqual(op.status, "abandoned")

    def test_keeps_recent_running_op(self):
        op = self._make("running", created_minutes_ago=10)
        cleanup_stuck_operations(max_age_minutes=60)
        op.refresh_from_db()
        self.assertEqual(op.status, "running")

    def test_does_not_touch_terminal_states(self):
        op = self._make("success", created_minutes_ago=600)
        cleanup_stuck_operations(max_age_minutes=60)
        op.refresh_from_db()
        self.assertEqual(op.status, "success")
