from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import anyio
from fastapi import APIRouter, Form, HTTPException, Request, Response, UploadFile
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from app.constants import (
    CONSERVATIVE_EXPANSION_FACTOR,
    EBML_MAGIC,
    FTYP_MAGIC,
    MAX_PCM_SIZE,
    MIME_TO_FORMAT,
    OGGS_MAGIC,
)
from app.config import get_storage_root
from app.storage_paths import ensure_job_dirs
from app.validation import read_and_validate_upload

try:
    from torch.cuda import OutOfMemoryError as CudaOOMError
except (ImportError, AttributeError):
    CudaOOMError = None

logger = logging.getLogger(__name__)

router = APIRouter()


def _job_http_exc(status_code: int, detail: str, job_id: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail, headers={"X-Job-Id": job_id})


def _detect_audio_type(contents: bytes) -> str | None:
    """Detect audio format from magic bytes. Returns base MIME type or None."""
    if len(contents) < 8:
        return None
    # EBML header (WebM / Matroska)
    if contents[:4] == EBML_MAGIC:
        return "audio/webm"
    if contents[:4] == OGGS_MAGIC:
        return "audio/ogg"
    # MP4: ftyp atom at offset 4 (not 0)
    if contents[4:8] == FTYP_MAGIC:
        return "audio/mp4"
    return None


class AudioConversionError(Exception):
    """Domain exception for audio conversion failures."""


class VoiceInferenceError(Exception):
    """Domain exception for XTTS v2 inference failures."""


class OOMError(VoiceInferenceError):
    """CUDA out-of-memory during inference."""


class NoOutputError(VoiceInferenceError):
    """XTTS produced no output file."""


class ShortAudioError(VoiceInferenceError):
    """Audio sample too short for voice cloning."""


def _estimate_pcm_size(contents: bytes, fmt: str) -> int | None:
    """Run ffprobe to estimate decompressed 16-bit PCM size without decoding.

    Returns estimated byte count, or None if metadata is unavailable.
    Raises FileNotFoundError if ffprobe binary is missing.
    """
    cmd = [
        "ffprobe", "-hide_banner",
        "-print_format", "json",
        "-show_format", "-show_streams",
        "-f", fmt, "pipe:0",
    ]
    try:
        result = subprocess.run(
            cmd, input=contents, capture_output=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        logger.debug("ffprobe timed out; skipping PCM size pre-check")
        return None

    try:
        info = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    streams = info.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio:
        return None
    s = audio[0]

    duration_str = s.get("duration") or info.get("format", {}).get("duration")
    sample_rate_str = s.get("sample_rate")
    channels = s.get("channels")
    if not all([duration_str, sample_rate_str, channels]):
        return None

    try:
        return int(float(duration_str) * int(sample_rate_str) * int(channels) * 2)
    except (ValueError, TypeError):
        return None


def _convert_to_wav(contents: bytes, fmt: str) -> tuple[bytes, float]:
    """Convert audio bytes to 16-bit PCM WAV using pydub.

    Returns:
        (wav_bytes, duration_secs): WAV bytes and audio duration in seconds.

    Raises:
        AudioConversionError: If decoding fails or decompressed PCM exceeds limit.
        FileNotFoundError: If FFmpeg is not installed.
    """
    estimated = _estimate_pcm_size(contents, fmt)
    if estimated is not None and estimated > MAX_PCM_SIZE:
        raise AudioConversionError("音訊解壓後超過大小限制。")
    if estimated is None:
        conservative = len(contents) * CONSERVATIVE_EXPANSION_FACTOR
        if conservative > MAX_PCM_SIZE:
            raise AudioConversionError("音訊解壓後超過大小限制。")

    try:
        audio = AudioSegment.from_file(io.BytesIO(contents), format=fmt)
    except FileNotFoundError:
        raise  # FFmpeg missing — let caller handle as 503
    except CouldntDecodeError as exc:
        raise AudioConversionError("無法解碼音訊檔案。") from exc

    if len(audio.raw_data) > MAX_PCM_SIZE:
        raise AudioConversionError("音訊解壓後超過大小限制。")

    duration_secs = len(audio) / 1000.0

    wav_buffer = io.BytesIO()
    try:
        audio.export(wav_buffer, format="wav")
    except Exception as exc:
        raise AudioConversionError("音訊編碼失敗。") from exc
    return wav_buffer.getvalue(), duration_secs


def _detect_language(text: str) -> str:
    """Detect language from text using Unicode script heuristics.

    Priority: Japanese (hiragana/katakana) > Korean (hangul)
    > Chinese (CJK ideographs) > English.
    Ambiguous kanji-only text defaults to 'zh-cn'.
    """
    has_cjk = False
    has_korean = False
    for ch in text:
        if '\u3040' <= ch <= '\u309f' or '\u30a0' <= ch <= '\u30ff':
            return "ja"
        if '\uac00' <= ch <= '\ud7af':
            has_korean = True
        elif '\u4e00' <= ch <= '\u9fff':
            has_cjk = True
    if has_korean:
        return "ko"
    if has_cjk:
        return "zh-cn"  # XTTS v2 僅支援 "zh-cn" 作為中文語言代碼
    return "en"


def _persist_job_artifacts(storage_root: Path, job_id: str, fmt: str, contents: bytes, stripped: str, result_bytes: bytes) -> None:
    input_dir, output_dir = ensure_job_dirs(storage_root, job_id)
    (input_dir / f"original.{fmt}").write_bytes(contents)
    (input_dir / "text.txt").write_text(stripped, encoding="utf-8")
    (output_dir / "cloned.wav").write_bytes(result_bytes)


def _run_xtts(tts, wav_bytes: bytes, text: str, language: str) -> bytes:
    """Run XTTS v2 inference synchronously.

    Creates a TemporaryDirectory to own both speaker.wav and synth.wav;
    both are cleaned up atomically on function exit.

    Raises:
        VoiceInferenceError: On XTTS-specific failures.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        speaker_path = os.path.join(tmpdir, "speaker.wav")
        synth_path = os.path.join(tmpdir, "synth.wav")
        with open(speaker_path, "wb") as f:
            f.write(wav_bytes)
        try:
            tts.tts_to_file(
                text=text,
                speaker_wav=speaker_path,
                language=language,
                file_path=synth_path,
            )
        except ValueError as exc:
            if "audio too short" in str(exc).lower():
                raise ShortAudioError("audio too short") from exc
            raise
        except Exception as exc:
            if CudaOOMError is not None and isinstance(exc, CudaOOMError):
                raise OOMError("CUDA out of memory") from exc
            raise
        if not os.path.isfile(synth_path):
            raise NoOutputError("no output file produced")
        with open(synth_path, "rb") as f:
            return f.read()


@router.post(
    "/api/clone-voice",
    summary="Clone a voice",
    description="Upload an audio sample and text to generate speech in the cloned voice.",
    tags=["voice"],
    response_class=Response,
    responses={
        200: {
            "content": {"audio/wav": {"schema": {"type": "string", "format": "binary"}}},
            "description": "Cloned voice audio (WAV)",
        },
        422: {"description": "Audio decode failure"},
        503: {"description": "Audio conversion service unavailable"},
    },
)
async def clone_voice(request: Request, file: UploadFile, text: Optional[str] = Form(None)) -> Response:
    # MIME type is informational only; final validation uses magic bytes.
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime not in MIME_TO_FORMAT:
        logger.debug("MIME hint %r not in MIME_TO_FORMAT; will rely on magic bytes", mime)

    job_id = str(uuid.uuid4())

    # Validate text
    stripped = (text or "").strip()
    if text is None or stripped == "":
        raise _job_http_exc(400, "文字不得為空。", job_id)
    if len(stripped) > 500:
        raise _job_http_exc(400, "文字不得超過 500 個字元。", job_id)

    # Validate file size + magic bytes
    try:
        contents, detected = await read_and_validate_upload(
            file,
            detect_type=_detect_audio_type,
            allowed_types=set(MIME_TO_FORMAT),
            type_error_detail="檔案內容不是有效的音訊格式。",
        )
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={**(exc.headers or {}), "X-Job-Id": job_id},
        ) from None

    fmt = MIME_TO_FORMAT[detected]

    # Convert to WAV
    try:
        wav_bytes, duration_secs = await anyio.to_thread.run_sync(
            lambda: _convert_to_wav(contents, fmt),
            abandon_on_cancel=True,
        )
    except AudioConversionError as exc:
        logger.warning("Audio conversion failed: %s", exc)
        raise _job_http_exc(422, str(exc), job_id) from None
    except FileNotFoundError:
        logger.error("FFmpeg binary not found")
        raise _job_http_exc(503, "音訊轉換服務暫時無法使用。", job_id) from None

    # Duration validation
    if duration_secs < 3.0:
        raise _job_http_exc(400, "音訊樣本太短，至少需要 3 秒。", job_id)

    # Model guard
    tts_model = getattr(request.app.state, "tts_model", None)
    if tts_model is None:
        raise _job_http_exc(503, "語音克隆服務尚未就緒。", job_id)

    language = _detect_language(stripped)

    async with request.app.state.xtts_admission_lock:
        if request.app.state.xtts_semaphore.locked():
            raise _job_http_exc(503, "語音克隆服務忙碌中，請稍後再試。", job_id)
        await request.app.state.xtts_semaphore.acquire()

    try:
        async with request.app.state.xtts_lock:
            result_bytes = await anyio.to_thread.run_sync(
                lambda: _run_xtts(tts_model, wav_bytes, stripped, language),
                abandon_on_cancel=False,
            )
    except OOMError:
        logger.warning("XTTS inference failed: CUDA OOM")
        raise _job_http_exc(503, "語音克隆服務資源不足，請稍後再試。", job_id) from None
    except NoOutputError:
        logger.warning("XTTS inference failed: no output file")
        raise _job_http_exc(503, "語音合成未產生輸出檔案。", job_id) from None
    except ShortAudioError:
        logger.warning("XTTS inference failed: audio too short")
        raise _job_http_exc(422, "音訊樣本太短，無法進行語音克隆。", job_id) from None
    except Exception:
        logger.exception("Unexpected XTTS error")
        raise _job_http_exc(500, "語音克隆服務發生未預期錯誤。", job_id) from None
    finally:
        request.app.state.xtts_semaphore.release()

    # Persist job artifacts — storage failure must not block the response.
    try:
        storage_root = get_storage_root()
        await anyio.to_thread.run_sync(
            lambda: _persist_job_artifacts(storage_root, job_id, fmt, contents, stripped, result_bytes),
            abandon_on_cancel=False,
        )
    except Exception:
        logger.exception("Failed to persist job artifacts for job_id=%s", job_id)

    return Response(
        content=result_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'attachment; filename="cloned.wav"',
            "X-Job-Id": job_id,
        },
    )
