"""Per-task peak-RSS measurement (CONVERTICA-59 follow-up).

The WorkerLostError incident was an OOM SIGKILL, not a time-limit hit, and one
heavy conversion can OOM-kill a sibling because the prefork children share one
container memory cgroup. Before changing worker concurrency / isolation we want
real data: how much memory does each conversion type actually use? Each
conversion now samples the worker process's peak resident-set size into
``OperationRun.peak_rss_mb``.

These tests pin the sampler behaviour and the model field so the measurement
keeps working.
"""

from __future__ import annotations

import time

from django.test import TestCase


class PeakRSSSamplerTests(TestCase):
    def test_records_a_positive_baseline_peak(self):
        from src.tasks.pdf_conversion import _PeakRSSSampler

        sampler = _PeakRSSSampler(interval=0.01)
        sampler.start()
        sampler.stop()
        self.assertIsNotNone(sampler.peak_mb)
        self.assertGreater(sampler.peak_mb, 0)

    def test_tracks_memory_growth_during_run(self):
        from src.tasks.pdf_conversion import _PeakRSSSampler

        sampler = _PeakRSSSampler(interval=0.01)
        sampler.start()
        baseline = sampler.peak_mb

        # Allocate ~80 MB and touch every page so RSS (not just VMS) grows,
        # then give the sampler thread time to observe the high-water mark.
        blob = bytearray(80 * 1024 * 1024)
        for i in range(0, len(blob), 4096):
            blob[i] = 1
        time.sleep(0.1)
        sampler.stop()
        peak = sampler.peak_mb
        del blob

        # The sampler must have seen the spike: at least +50 MB over baseline.
        self.assertGreater(peak, baseline + 50)

    def test_stop_is_idempotent(self):
        from src.tasks.pdf_conversion import _PeakRSSSampler

        sampler = _PeakRSSSampler(interval=0.01)
        sampler.start()
        sampler.stop()
        sampler.stop()  # must not raise

    def test_peak_mb_before_start_is_none(self):
        from src.tasks.pdf_conversion import _PeakRSSSampler

        sampler = _PeakRSSSampler(interval=0.01)
        self.assertIsNone(sampler.peak_mb)


class OperationRunPeakRSSFieldTests(TestCase):
    def test_field_is_nullable_and_persists(self):
        from src.users.models import OperationRun

        run = OperationRun.objects.create(conversion_type="compress_pdf")
        self.assertIsNone(run.peak_rss_mb)

        run.peak_rss_mb = 512
        run.save(update_fields=["peak_rss_mb"])
        run.refresh_from_db()
        self.assertEqual(run.peak_rss_mb, 512)
