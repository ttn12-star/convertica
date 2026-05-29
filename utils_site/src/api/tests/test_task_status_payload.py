"""Tests for async task-status payload mapping (CONVERTICA review B4).

A task that hits the soft time limit (or fails validation/corruption checks)
RETURNS {"status": "error", ...} instead of raising. Celery then records the
task as SUCCESS, so the status endpoint told the user "Conversion complete.
Download your file." — and the result endpoint then 404'd. The payload builder
must treat a SUCCESS result whose dict says status==error as a failure.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from src.api.async_views import build_task_status_payload


class TaskStatusPayloadTests(SimpleTestCase):
    def test_success_with_error_result_is_reported_as_failure(self):
        payload = build_task_status_payload(
            "t1",
            "SUCCESS",
            {"status": "error", "error": "Task exceeded time limit"},
        )
        self.assertNotIn("Conversion complete", payload.get("message", ""))
        self.assertEqual(payload.get("error"), "Task exceeded time limit")
        self.assertEqual(payload.get("progress"), 0)

    def test_genuine_success_reports_complete(self):
        payload = build_task_status_payload(
            "t2", "SUCCESS", {"output_filename": "out.pdf"}
        )
        self.assertEqual(payload.get("progress"), 100)
        self.assertEqual(payload.get("output_filename"), "out.pdf")
        self.assertIn("complete", payload.get("message", "").lower())

    def test_failure_status_reports_error(self):
        payload = build_task_status_payload("t3", "FAILURE", "boom")
        self.assertEqual(payload.get("progress"), 0)
        self.assertIn("boom", payload.get("error", ""))

    def test_progress_status_passes_through_progress(self):
        payload = build_task_status_payload(
            "t4", "PROGRESS", {"progress": 42, "current_step": "Converting"}
        )
        self.assertEqual(payload.get("progress"), 42)
        self.assertEqual(payload.get("current_step"), "Converting")
