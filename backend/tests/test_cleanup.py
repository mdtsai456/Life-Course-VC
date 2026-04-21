"""Tests for job artifact cleanup."""

from __future__ import annotations

import asyncio
import os
import time
from unittest.mock import patch

from app.cleanup import _sweep_once, cleanup_expired_jobs


def _make_job_dir(root, subdir, job_id, age_seconds):
    d = root / subdir / job_id
    d.mkdir(parents=True)
    (d / "payload.bin").write_bytes(b"x")
    mtime = time.time() - age_seconds
    os.utime(d, (mtime, mtime))
    return d


class TestSweepOnce:
    def test_removes_expired_dirs(self, tmp_path):
        ttl = 60
        fresh = _make_job_dir(tmp_path, "input", "fresh", age_seconds=10)
        stale_in = _make_job_dir(tmp_path, "input", "stale", age_seconds=120)
        stale_out = _make_job_dir(tmp_path, "output", "stale", age_seconds=120)

        removed = _sweep_once(tmp_path, ttl)

        assert removed == 2
        assert fresh.is_dir()
        assert not stale_in.exists()
        assert not stale_out.exists()

    def test_no_storage_dirs_returns_zero(self, tmp_path):
        assert _sweep_once(tmp_path, 60) == 0

    def test_partial_dirs(self, tmp_path):
        (tmp_path / "input").mkdir()
        # Only input/ exists; output/ absent — should not crash.
        stale = _make_job_dir(tmp_path, "input", "stale", age_seconds=999)
        removed = _sweep_once(tmp_path, 60)
        assert removed == 1
        assert not stale.exists()

    def test_zero_ttl_skips(self, tmp_path):
        """ttl<=0 disables cleanup entirely."""
        d = _make_job_dir(tmp_path, "input", "anything", age_seconds=9999)
        assert _sweep_once(tmp_path, 0) == 0
        assert d.is_dir()

    def test_ignores_non_directory_entries(self, tmp_path):
        (tmp_path / "input").mkdir()
        # A loose file in input/ (not a job dir) — must be ignored.
        stray = tmp_path / "input" / "loose.txt"
        stray.write_text("ignore me")
        # Age a real job dir so something is deleted.
        stale = _make_job_dir(tmp_path, "input", "stale", age_seconds=999)
        removed = _sweep_once(tmp_path, 60)
        assert removed == 1
        assert stray.exists()
        assert not stale.exists()

    def test_only_counts_dirs_removed(self, tmp_path):
        stale = _make_job_dir(tmp_path, "input", "stale", age_seconds=999)

        with patch("app.cleanup.shutil.rmtree") as mock_rmtree:
            removed = _sweep_once(tmp_path, 60)

        assert removed == 0
        assert stale.exists()
        mock_rmtree.assert_called_once_with(stale, ignore_errors=True)


class TestCleanupExpiredJobsAsync:
    def test_async_wrapper(self, tmp_path):
        """The async wrapper runs the sweep in a worker thread."""
        _make_job_dir(tmp_path, "output", "old", age_seconds=999)
        loop = asyncio.new_event_loop()
        try:
            removed = loop.run_until_complete(cleanup_expired_jobs(tmp_path, 60))
        finally:
            loop.close()
        assert removed == 1
