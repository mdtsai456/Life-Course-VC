"""Job artifact status & download endpoints."""

from __future__ import annotations

import logging
import stat as stat_module
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_storage_root
from app.storage_paths import job_output_dir

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_job_id(job_id: str) -> None:
    try:
        uuid.UUID(job_id)
    except ValueError:
        # Return 404 (not 400) to avoid revealing whether the id was malformed
        # vs simply absent, and to deny any path-traversal probing.
        raise HTTPException(status_code=404, detail="job not found") from None


def _audio_path_and_stat_or_404(job_id: str):
    audio_path = job_output_dir(get_storage_root(), job_id) / "cloned.wav"
    try:
        audio_stat = audio_path.stat()
    except OSError:
        raise HTTPException(status_code=404, detail="job not found") from None
    if not stat_module.S_ISREG(audio_stat.st_mode):
        raise HTTPException(status_code=404, detail="job not found")
    return audio_path, audio_stat


@router.get(
    "/api/jobs/{job_id}",
    summary="Get job metadata",
    tags=["jobs"],
    responses={404: {"description": "Job not found"}},
)
async def get_job(job_id: str) -> dict:
    _validate_job_id(job_id)
    _audio_path, audio_stat = _audio_path_and_stat_or_404(job_id)
    return {
        "job_id": job_id,
        "status": "completed",
        "audio_url": f"/api/jobs/{job_id}/audio",
        "created_at": datetime.fromtimestamp(audio_stat.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": audio_stat.st_size,
    }


@router.get(
    "/api/jobs/{job_id}/audio",
    summary="Download job audio output",
    tags=["jobs"],
    response_class=FileResponse,
    responses={
        200: {"content": {"audio/wav": {}}, "description": "Cloned voice audio (WAV)"},
        404: {"description": "Job not found"},
    },
)
async def get_job_audio(job_id: str) -> FileResponse:
    _validate_job_id(job_id)
    audio_path, _ = _audio_path_and_stat_or_404(job_id)
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename="cloned.wav",
    )
