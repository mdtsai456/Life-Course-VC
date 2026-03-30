"""Shared constants used across route modules."""

from __future__ import annotations

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

FILE_TOO_LARGE_DETAIL = f"檔案過大，最大允許 {MAX_FILE_SIZE // (1024 * 1024)} MB。"

# Audio magic bytes
EBML_MAGIC = b"\x1a\x45\xdf\xa3"  # WebM / Matroska
OGGS_MAGIC = b"OggS"              # Ogg Vorbis / Opus
FTYP_MAGIC = b"ftyp"              # MP4 / ISO BMFF (at offset 4)

# Voice route constants
MAX_PCM_SIZE = 50 * 1024 * 1024  # 50 MB decompressed PCM limit
MAX_XTTS_PENDING = 4  # 1 running + 3 queued; beyond this → 503
MIME_TO_FORMAT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "audio/ogg": "ogg",
}
