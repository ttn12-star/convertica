"""Regression guard for CONVERTICA-59 (WorkerLostError poison-pill loop).

A conversion that exhausts the worker's memory is SIGKILLed by the OOM
killer. With ``reject_on_worker_lost=True`` Celery re-queues such a task,
so it runs again, OOMs again, and re-kills a worker — an unbounded loop
that produced 23 back-to-back WorkerLostError SIGKILLs in production.

These tests pin the flag to ``False`` (both the global default and the
heavy-conversion task) so the poison-pill behaviour cannot silently come
back. ``acks_late`` stays ``True`` — we still want at-least-once delivery
for ordinary failures; we just don't want to re-run a task that already
killed its worker.
"""

from __future__ import annotations

from django.test import TestCase


class RejectOnWorkerLostConfigTests(TestCase):
    def test_global_default_is_false(self):
        from utils_site.celery import app

        self.assertFalse(
            app.conf.task_reject_on_worker_lost,
            "task_reject_on_worker_lost must stay False — re-queuing an "
            "OOM-killed task creates a poison-pill loop (CONVERTICA-59).",
        )
        # at-least-once delivery for normal failures is still wanted
        self.assertTrue(app.conf.task_acks_late)

    def test_generic_conversion_task_is_false(self):
        from src.tasks.pdf_conversion import generic_conversion_task

        self.assertFalse(
            generic_conversion_task.reject_on_worker_lost,
            "generic_conversion_task must not requeue on worker loss "
            "(CONVERTICA-59).",
        )
