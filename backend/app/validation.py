"""Shared upload validation helpers."""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from typing import Callable

from fastapi import HTTPException, UploadFile

from app.constants import FILE_TOO_LARGE_DETAIL, MAX_FILE_SIZE


async def read_and_validate_upload(
    file: UploadFile,
    *,
    max_size: int = MAX_FILE_SIZE,
    detect_type: Callable[[bytes], str | None] | None = None,
    allowed_types: AbstractSet[str] | None = None,
    type_error_detail: str = "不支援的檔案類型。",
) -> tuple[bytes, str | None]:
    """Read an upload file with size and optional type validation.

    Returns:
        (contents, detected_type) where detected_type is the result of
        detect_type(contents) if provided, else None.

    Raises:
        HTTPException 413 if the file exceeds max_size.
        HTTPException 415 if detect_type returns a type not in allowed_types.
    """
    if allowed_types is not None and detect_type is None:
        raise ValueError(
            "allowed_types requires a detect_type callback to perform type validation"
        )

    if file.size is not None and file.size > max_size:
        raise HTTPException(status_code=413, detail=FILE_TOO_LARGE_DETAIL)

    contents = await file.read(max_size + 1)
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail=FILE_TOO_LARGE_DETAIL)

    detected = None
    if detect_type is not None:
        detected = detect_type(contents)
        if allowed_types is not None and detected not in allowed_types:
            raise HTTPException(status_code=415, detail=type_error_detail)

    return contents, detected
