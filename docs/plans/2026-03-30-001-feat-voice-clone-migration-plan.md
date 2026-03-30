---
title: "feat: Port Voice Cloning from Remove-Background to Kinshasa"
type: feat
status: active
date: 2026-03-30
origin: docs/brainstorms/2026-03-30-voice-clone-migration-requirements.md
---

# feat: Port Voice Cloning from Remove-Background to Kinshasa

## Overview

Port the Voice Cloning feature (Coqui XTTS v2) from Life-Course-Remove-Background-main into the kinshasa project as a standalone dedicated app. Backend first, then frontend. Faithful port — no functional changes.

## Problem Frame

The kinshasa project needs Voice Cloning as a standalone app rather than part of a multi-tool suite. The source project (`Life-Course-Remove-Background-main`) has a working implementation that should be ported with minimal modification, stripping only the unrelated features (background removal, image-to-3D).

(see origin: `docs/brainstorms/2026-03-30-voice-clone-migration-requirements.md`)

## Requirements Trace

- R1. FastAPI app with `POST /api/clone-voice` endpoint
- R2. XTTS v2 model loading on startup via FastAPI lifespan
- R3. Audio validation (≤10 MB, webm/mp4/ogg, magic bytes check)
- R4. Language auto-detection (Chinese/English) based on Unicode CJK ranges
- R5. WAV output at 24 kHz
- R6. Concurrency control via asyncio.Lock + Semaphore for GPU safety
- R7. Health check endpoint (`GET /health`)
- R8. CORS middleware configuration
- R9. React + Vite app with VoiceCloner component
- R10. Microphone recording UI
- R11. Text input for cloned speech
- R12. Audio playback of results
- R13. API client service for clone-voice endpoint

## Scope Boundaries

- No background removal, no image-to-3D
- No functional changes or improvements to voice cloning logic
- No Docker/deployment setup
- Python venv required; Node.js via nvm required

## Context & Research

### Source Project

Source: `/Users/b40160/Downloads/Life-Course/Life-Course-Remove-Background-main`

### Relevant Code and Patterns

**Backend (to port):**
- `backend/app/routes/voice.py` (297 lines) — core endpoint, port as-is
- `backend/app/main.py` — lifespan, middleware, routers; needs stripping of rembg/image/3D code
- `backend/app/config.py` — CORS + docs toggle from env vars; port as-is
- `backend/app/constants.py` — magic bytes, size limits; strip image-only constants
- `backend/app/validation.py` — `read_and_validate_upload`; port as-is
- `backend/tests/conftest.py` — sys.modules patching for torch/TTS; remove rembg patches
- `backend/tests/test_voice.py` (44 tests) — port as-is

**Frontend (to port):**
- `frontend/src/components/VoiceCloner.jsx` (318 lines) — main UI; port as-is
- `frontend/src/components/LoadingButton.jsx` — reusable button; port as-is
- `frontend/src/components/ProgressStatus.jsx` — progress bar; port as-is
- `frontend/src/components/ErrorBoundary.jsx` — error boundary; port as-is
- `frontend/src/hooks/useAsyncSubmit.js` — async submit hook; port as-is
- `frontend/src/hooks/useObjectUrl.js` — object URL lifecycle; port as-is
- `frontend/src/utils/revokeResultUrl.js` — cleanup utility; port as-is
- `frontend/src/services/api.js` — strip non-voice functions, keep `postForBlob` + `cloneVoice`
- `frontend/src/App.jsx` — rewrite: single feature, no tabs
- `frontend/src/main.jsx` — remove `@google/model-viewer` import
- `frontend/index.html` — update title
- `frontend/src/index.css` — strip image/3D-specific styles
- `frontend/package.json` — remove `@google/model-viewer`
- `frontend/vite.config.js` — port as-is

### What to Skip

**Backend:** `routes/images.py`, `routes/threed.py`, `rembg` dependency, `pillow` dependency
**Frontend:** `ImageUploader.jsx`, `ImageTo3D.jsx`, `validateImageFile.js`, `constants.js`, `@google/model-viewer`

## Key Technical Decisions

- **Keep modular file structure**: The separation of routes/, config.py, constants.py, validation.py is clean and the test infrastructure depends on these module paths. Collapsing would require rewriting all test patches.
- **Strip rather than rewrite**: Remove non-voice code from shared files (main.py, constants.py, conftest.py) rather than rewriting from scratch. This preserves tested patterns.
- **Single-feature frontend**: Remove tab navigation from App.jsx, render VoiceCloner directly.

## Open Questions

### Resolved During Planning

- **File structure (modular vs single file):** Keep modular — tests depend on module paths, and the structure is already clean.
- **Frontend simplification:** Remove tabs, render VoiceCloner directly. No tab switching needed for a single feature.

### Deferred to Implementation

- **Exact CSS to strip from index.css:** Will need to identify which styles are image/3D-specific vs shared during implementation.

## Implementation Units

- [ ] **Unit 1: Backend project structure and dependencies**

  **Goal:** Create the backend directory structure, port config/constants/validation, and set up requirements.txt with venv.

  **Requirements:** R1, R3, R8

  **Dependencies:** None

  **Files:**
  - Create: `backend/app/__init__.py`
  - Create: `backend/app/config.py` (from source)
  - Create: `backend/app/constants.py` (stripped of image constants)
  - Create: `backend/app/validation.py` (from source)
  - Create: `backend/app/routes/__init__.py`
  - Create: `backend/requirements.txt` (voice-only deps)

  **Approach:**
  - Copy `config.py` and `validation.py` as-is from source
  - Copy `constants.py` and remove: `PNG_MAGIC`, `JPEG_MAGIC`, `WEBP_MAGIC_RIFF`, `WEBP_MAGIC_TAG`, `ALLOWED_IMAGE_MIME_TYPES`, `ALLOWED_3D_MIME_TYPES`
  - Create `requirements.txt` with only voice-cloning dependencies (fastapi, uvicorn, python-multipart, pydub, anyio, coqui-tts, torch, torchaudio, httpx, pytest, pytest-asyncio)
  - Set up Python venv: `python -m venv .venv`

  **Patterns to follow:** Source project file structure at `backend/app/`

  **Test expectation:** none — scaffolding only, tested via Unit 3

  **Verification:** Directory structure exists, venv created, `pip install -r requirements.txt` succeeds in venv

- [ ] **Unit 2: Port voice route and FastAPI main**

  **Goal:** Port the voice cloning endpoint and simplified FastAPI app entry point.

  **Requirements:** R1, R2, R4, R5, R6, R7, R8

  **Dependencies:** Unit 1

  **Files:**
  - Create: `backend/app/routes/voice.py` (from source, as-is)
  - Create: `backend/app/main.py` (from source, stripped of rembg/image/3D)

  **Approach:**
  - Copy `voice.py` exactly from source
  - Copy `main.py` and remove:
    - `from rembg import new_session` import
    - `from app.routes.images import router as images_router`
    - `from app.routes.threed import router as threed_router`
    - rembg session creation/teardown in lifespan
    - `app.include_router(images_router)` and `app.include_router(threed_router)`
    - `rembg` entry from health check dict
  - Keep: torch/TTS imports, XTTS v2 lifespan loading, voice_router, CORS middleware, security headers, health endpoint

  **Patterns to follow:** Source `main.py` lifespan pattern, source `voice.py` endpoint pattern

  **Test scenarios:**
  - Happy path: `POST /api/clone-voice` with valid audio + text returns 200 with WAV content-type
  - Happy path: `GET /health` returns 200 with xtts_v2 status
  - Edge case: Text exactly 500 characters is accepted
  - Edge case: Audio exactly at 3-second minimum duration is accepted
  - Error path: Empty text returns 422
  - Error path: Text > 500 characters returns 422
  - Error path: File > 10MB returns 413
  - Error path: Invalid audio format (not webm/mp4/ogg) returns 415
  - Error path: Audio < 3 seconds returns 422
  - Error path: Semaphore full (all slots occupied) returns 503

  **Verification:** `pytest` passes in venv; `curl` test against running server returns valid WAV

- [ ] **Unit 3: Port backend tests**

  **Goal:** Port test suite and conftest, adapted for the standalone app.

  **Requirements:** R1-R8

  **Dependencies:** Unit 2

  **Files:**
  - Create: `backend/tests/__init__.py`
  - Create: `backend/tests/conftest.py` (from source, simplified)
  - Create: `backend/tests/test_voice.py` (from source, as-is)

  **Approach:**
  - Copy `test_voice.py` as-is from source
  - Copy `conftest.py` and remove:
    - `PNG_HEADER` constant
    - `app.routes.images` and `app.routes.threed` from `_APP_MODULES`
    - rembg mocking from `_make_standard_patches` and `client` fixture
  - Keep: torch/TTS sys.modules patching (needed since main.py imports them at module level)

  **Patterns to follow:** Source `conftest.py` sys.modules patching strategy

  **Test scenarios:**
  - Happy path: All 44 existing voice tests pass after conftest adaptation
  - Edge case: Tests run without GPU (mocked TTS model)

  **Verification:** `pytest -v` in venv shows all tests passing

- [ ] **Unit 4: Frontend project structure and dependencies**

  **Goal:** Create the React + Vite frontend with only voice-cloning dependencies.

  **Requirements:** R9, R13

  **Dependencies:** None (can run in parallel with backend units)

  **Files:**
  - Create: `frontend/index.html` (from source, updated title)
  - Create: `frontend/package.json` (from source, without `@google/model-viewer`)
  - Create: `frontend/vite.config.js` (from source, as-is)
  - Create: `frontend/src/main.jsx` (from source, without model-viewer import)

  **Approach:**
  - Copy `index.html`, update `<title>` to "Voice Clone" or similar
  - Copy `package.json`, remove `@google/model-viewer` from dependencies
  - Copy `vite.config.js` as-is (API proxy to backend port 8000)
  - Copy `main.jsx`, remove `import '@google/model-viewer'` line
  - Use nvm for Node.js version management

  **Patterns to follow:** Source frontend structure

  **Test expectation:** none — scaffolding only, tested via Unit 6

  **Verification:** `npm install` succeeds, `npm run dev` starts without errors

- [ ] **Unit 5: Port VoiceCloner UI and supporting components**

  **Goal:** Port all voice cloning frontend components, hooks, utils, and API service.

  **Requirements:** R9, R10, R11, R12, R13

  **Dependencies:** Unit 4

  **Files:**
  - Create: `frontend/src/components/VoiceCloner.jsx` (from source, as-is)
  - Create: `frontend/src/components/LoadingButton.jsx` (from source, as-is)
  - Create: `frontend/src/components/ProgressStatus.jsx` (from source, as-is)
  - Create: `frontend/src/components/ErrorBoundary.jsx` (from source, as-is)
  - Create: `frontend/src/hooks/useAsyncSubmit.js` (from source, as-is)
  - Create: `frontend/src/hooks/useObjectUrl.js` (from source, as-is)
  - Create: `frontend/src/utils/revokeResultUrl.js` (from source, as-is)
  - Create: `frontend/src/services/api.js` (from source, voice-only functions)

  **Approach:**
  - Copy all component, hook, and util files as-is
  - Copy `api.js` and keep only: `API_BASE`, `postForBlob` helper, `cloneVoice` function. Remove `removeBackground` and `convertTo3D`.

  **Patterns to follow:** Source component structure

  **Test expectation:** none — UI components, tested manually in Unit 6

  **Verification:** No import errors when app loads

- [ ] **Unit 6: Simplify App.jsx and index.css for single-feature app**

  **Goal:** Create a simplified App.jsx (no tabs) and strip non-voice styles from index.css.

  **Requirements:** R9

  **Dependencies:** Unit 5

  **Files:**
  - Create: `frontend/src/App.jsx` (simplified from source)
  - Create: `frontend/src/index.css` (from source, stripped of image/3D styles)

  **Approach:**
  - Rewrite `App.jsx`: remove tab navigation, import and render `VoiceCloner` directly wrapped in `ErrorBoundary`. Keep the app header/title.
  - Copy `index.css` and remove styles specific to `ImageUploader`, `ImageTo3D`, and tab navigation. Keep global styles, voice-cloner styles, and shared component styles.

  **Patterns to follow:** Source `App.jsx` structure, simplified

  **Test scenarios:**
  - Happy path: App loads and shows VoiceCloner component directly (no tabs visible)
  - Happy path: User can record audio, enter text, submit, and hear cloned speech
  - Edge case: Page reload preserves expected state (no stale recordings)

  **Verification:** Full end-to-end manual test: open browser → record audio → enter text → submit → hear cloned voice playback

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| XTTS v2 model download (~2.1 GB) on first run | Expected behavior; model caches after first download |
| FFmpeg not installed on target machine | Document as prerequisite; `pydub` will fail clearly |
| CUDA not available | Source code already handles CPU fallback |
| conftest sys.modules patching breaks after import changes | Keep same module paths as source to minimize patch changes |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-30-voice-clone-migration-requirements.md](docs/brainstorms/2026-03-30-voice-clone-migration-requirements.md)
- **Source project:** `/Users/b40160/Downloads/Life-Course/Life-Course-Remove-Background-main`
