"""Background cleanup of expired job artifacts."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path

import anyio

logger = logging.getLogger(__name__)


def _sweep_once(storage_root: Path, ttl_seconds: int) -> int:
    """Synchronously delete job dirs older than ttl. Returns count removed."""
    if ttl_seconds <= 0:
        return 0
    cutoff = time.time() - ttl_seconds
    removed = 0
    for subdir in ("input", "output"):
        d = storage_root / subdir
        if not d.is_dir():
            continue
        for job_dir in d.iterdir():
            if not job_dir.is_dir():
                continue
            try:
                if job_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    if not job_dir.exists():
                        removed += 1
            except OSError:
                logger.exception("cleanup failed for %s", job_dir)
    return removed


async def cleanup_expired_jobs(storage_root: Path, ttl_seconds: int) -> int:
    """Async wrapper running the sweep in a worker thread."""
    return await anyio.to_thread.run_sync(_sweep_once, storage_root, ttl_seconds)


async def cleanup_loop(storage_root: Path, ttl_seconds: int, interval_seconds: int) -> None:
    """Run cleanup repeatedly until cancelled."""
    while True:
        try:
            n = await cleanup_expired_jobs(storage_root, ttl_seconds)
            if n:
                logger.info("cleanup removed %d expired job dir(s)", n)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("cleanup iteration failed")
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
