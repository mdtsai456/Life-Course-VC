---
title: "feat: Add persistent job storage for voice cloning audio"
type: feat
status: completed
date: 2026-03-31
---

# feat: Add persistent job storage for voice cloning audio

## Overview

Add persistent file storage so that user-uploaded audio recordings and voice cloning output audio are saved to disk in a structured directory layout under a configurable `STORAGE_ROOT`. This mirrors the existing pattern in the sister REMBG project.

## Problem Frame

Currently, the voice cloning endpoint processes audio entirely in memory and temp files. Nothing persists after the HTTP response is sent. The user wants the same job-based storage pattern used in the REMBG project — input and output audio saved to `{STORAGE_ROOT}/input/{job_id}/` and `{STORAGE_ROOT}/output/{job_id}/` respectively.

## Requirements Trace

- R1. User-uploaded audio is persisted to `{STORAGE_ROOT}/input/{job_id}/` after successful inference
- R2. Voice cloning output audio is persisted to `{STORAGE_ROOT}/output/{job_id}/` after successful inference
- R3. `STORAGE_ROOT` is configurable via environment variable, defaulting to `./storage`
- R4. Each request gets a unique job ID (UUID), returned in an `X-Job-Id` response header
- R5. `storage/` directory is gitignored
- R6. Storage failure is logged but does not block the response — the user still receives the cloned audio
- R7. The text input (`text`) is persisted to `{STORAGE_ROOT}/input/{job_id}/text.txt`

## Scope Boundaries

- No cleanup/retention policy — files persist indefinitely (same as REMBG)
- No database or metadata storage — job structure is implicit in directory naming
- No API to retrieve stored files — storage is write-only for now
- No cloud storage integration — local filesystem only
- Frontend is unchanged

## Context & Research

### Relevant Code and Patterns

- **REMBG reference:** `storage_paths.py` — `job_input_dir()`, `job_output_dir()`, `ensure_job_dirs()`
- **REMBG config:** `config.py` — `get_storage_root()` reads `STORAGE_ROOT` env var, defaults to `./storage`, returns resolved `Path`
- **REMBG route integration:** `images.py` route — generates UUID after validation, persists input/output after processing, adds `X-Job-Id` header, raises HTTP 500 on storage failure
- **VC config pattern:** `backend/app/config.py` uses standalone `get_<setting>()` functions reading `os.getenv()`
- **VC test pattern:** `backend/tests/` uses `conftest.py` fixtures, class-based test organization, `sys.modules` patching for torch/TTS

## Key Technical Decisions

- **Follow REMBG pattern for module structure:** Same module structure (`storage_paths.py`), same config function signature, same directory layout. Rationale: consistency across sister projects, proven pattern, reduces cognitive overhead.
- **Save input as original format (not WAV):** Store the raw uploaded bytes (`contents`) to preserve the original file. File name: `original.{fmt}` (e.g., `original.webm`, `original.ogg`, `original.mp4`). The `fmt` variable from `MIME_TO_FORMAT[detected]` is already available. This matches REMBG's approach of storing raw upload bytes.
- **Save text input alongside audio:** Persist the `text` parameter as `text.txt` in the input directory. Cost is negligible, and it makes jobs self-contained for debugging or replay.
- **Save output as WAV:** The inference result is already WAV bytes. File name: `cloned.wav`.
- **Storage writes happen after successful inference:** If inference fails, no files are stored. This prevents orphaned input-only directories.
- **Storage writes placed after semaphore release:** Storage I/O must not occupy an inference semaphore slot. Writes happen after `xtts_semaphore.release()` and before `return Response(...)`.
- **Storage failure does not block the response:** Unlike REMBG (which raises HTTP 500), voice cloning inference is expensive (GPU, semaphore-limited). If inference succeeds but storage fails, log the error and still return the audio to the user.

## Open Questions

### Resolved During Planning

- **What format to store input?** Original upload format (`contents`), not WAV. Preserves the original file for debugging. File name: `original.{fmt}`.
- **When to generate job_id?** After validation succeeds, before inference. This matches the REMBG pattern.
- **Where to place storage writes?** After `xtts_semaphore.release()`, before `return Response(...)`. Disk I/O must not occupy inference semaphore slots.
- **What happens on storage failure?** Log error, still return audio to user. Inference is too expensive to discard on a disk write failure.
- **Should we store the text input?** Yes, as `text.txt` in the input directory.

## Implementation Units

- [x] **Unit 1: Add `get_storage_root()` to config and create `storage_paths.py`**

  **Goal:** Establish storage infrastructure modules

  **Requirements:** R3

  **Dependencies:** None

  **Files:**
  - Modify: `backend/app/config.py`
  - Create: `backend/app/storage_paths.py`
  - Modify: `backend/tests/conftest.py` (add `app.storage_paths` to `_APP_MODULES`)
  - Create: `backend/tests/test_storage_paths.py`

  **Approach:**
  - Add `get_storage_root() -> Path` to `config.py` following the existing `get_<setting>()` pattern. Default `./storage`, add comment noting CWD dependency (same as REMBG)
  - Create `storage_paths.py` with `job_input_dir()`, `job_output_dir()`, `ensure_job_dirs()` — mirror REMBG's module
  - Use `from __future__ import annotations` and type annotations per project convention

  **Patterns to follow:**
  - REMBG `storage_paths.py` and `config.py`
  - Existing `config.py` function style in this project

  **Test scenarios:**
  - Happy path: `get_storage_root()` returns resolved Path from env var
  - Happy path: `get_storage_root()` returns default `./storage` when env var is unset
  - Happy path: `job_input_dir()` returns `storage_root / "input" / job_id`
  - Happy path: `job_output_dir()` returns `storage_root / "output" / job_id`
  - Happy path: `ensure_job_dirs()` creates both directories and returns the paths
  - Edge case: `ensure_job_dirs()` succeeds when directories already exist

  **Verification:**
  - All tests pass; module imports cleanly

- [x] **Unit 2: Integrate storage into the voice cloning endpoint**

  **Goal:** Persist input and output audio on successful requests, return job ID in response header

  **Requirements:** R1, R2, R4, R6, R7

  **Dependencies:** Unit 1

  **Files:**
  - Modify: `backend/app/routes/voice.py`
  - Modify: `backend/tests/test_voice.py`

  **Approach:**
  - After validation, generate `job_id = str(uuid.uuid4())`
  - After `xtts_semaphore.release()` (line 303) and before `return Response(...)`, call `ensure_job_dirs()` and write:
    - `original.{fmt}` — raw upload bytes (`contents`) to input dir
    - `text.txt` — the text parameter (`stripped`) to input dir
    - `cloned.wav` — inference result (`result_bytes`) to output dir
  - Add `X-Job-Id` header to the response
  - Wrap storage writes in try/except — log error but still return audio (inference is too expensive to discard)

  **Patterns to follow:**
  - REMBG `images.py` route integration pattern
  - Existing error handling style in `voice.py`

  **Test scenarios:**
  - Happy path: successful request creates `input/{job_id}/original.{fmt}`, `input/{job_id}/text.txt`, and `output/{job_id}/cloned.wav`
  - Happy path: response includes `X-Job-Id` header with valid UUID
  - Happy path: saved input file contains the raw upload bytes (not WAV-converted)
  - Happy path: saved text.txt contains the text parameter
  - Happy path: saved output file contains the inference result bytes
  - Error path: storage write failure logs error but response still returns audio with 200
  - Integration: files are NOT created when validation fails (bad format, too large)
  - Integration: files are NOT created when inference fails

  **Verification:**
  - All existing tests still pass; new storage tests pass; files appear in expected paths during test

- [x] **Unit 3: Add `storage/` to `.gitignore`**

  **Goal:** Prevent stored audio files from being committed

  **Requirements:** R5

  **Dependencies:** None

  **Files:**
  - Modify: `.gitignore`

  **Approach:**
  - Add `storage/` entry to the project-level `.gitignore`

  **Test expectation:** none — pure config change

  **Verification:**
  - `git check-ignore storage/test` returns a match

## System-Wide Impact

- **Interaction graph:** Only the `/api/clone-voice` endpoint is affected. No middleware, callbacks, or other routes are involved.
- **Error propagation:** Storage failure → logged error, response still succeeds. Does not affect model state or concurrency controls.
- **State lifecycle risks:** Minimal. Files accumulate indefinitely with no cleanup. Disk space could eventually become a concern but is explicitly out of scope.
- **API surface parity:** The `X-Job-Id` header is a new addition to the response. Frontend does not need to consume it.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Disk fills up over time | Out of scope per requirements; can add retention policy later |
| Storage path permissions | `mkdir(parents=True, exist_ok=True)` + log error on failure |

## Sources & References

- REMBG reference: sister project `storage_paths.py` — `job_input_dir()`, `job_output_dir()`, `ensure_job_dirs()`
- REMBG config: sister project `config.py` — `get_storage_root()`
- REMBG route: sister project `routes/images.py` — job storage integration pattern
