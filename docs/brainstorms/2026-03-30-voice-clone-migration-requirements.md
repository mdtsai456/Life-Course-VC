---
date: 2026-03-30
topic: voice-clone-migration
---

# Voice Cloning Migration to Kinshasa

## Problem Frame
The kinshasa project needs Voice Cloning functionality identical to what exists in Life-Course-Remove-Background-main. Rather than maintaining it as part of a multi-tool suite, kinshasa will be a dedicated Voice Cloning app.

## Requirements

**Backend (Phase 1)**
- R1. FastAPI app with `POST /api/clone-voice` endpoint, ported from existing `voice.py`
- R2. XTTS v2 model loading on startup via FastAPI lifespan
- R3. Audio validation (≤10 MB, webm/mp4/ogg, magic bytes check)
- R4. Language auto-detection (Chinese/English) based on Unicode CJK ranges
- R5. WAV output at 24 kHz
- R6. Concurrency control via asyncio.Lock + Semaphore for GPU safety
- R7. Health check endpoint (`GET /health`)
- R8. CORS middleware configuration

**Frontend (Phase 2)**
- R9. React + Vite app with VoiceCloner component
- R10. Microphone recording UI
- R11. Text input for cloned speech
- R12. Audio playback of results
- R13. API client service for clone-voice endpoint

## Success Criteria
- Backend: `POST /api/clone-voice` returns valid WAV audio matching the source project's behavior
- Frontend: User can record audio, enter text, and hear cloned speech
- Existing tests from source project pass when adapted

## Scope Boundaries
- No background removal feature
- No image-to-3D feature
- No redesign or improvements — faithful port of existing code
- No Docker/deployment setup in initial scope

## Constraints
- Python: Must use `venv` — do not install packages globally
- Node.js: Must use `nvm` — do not pollute local Node environment

## Key Decisions
- **FastAPI**: Same framework as source project for consistency
- **Backend first**: Validate core functionality before building UI
- **Standalone app**: Only Voice Cloning, no other features
- **Faithful port**: No functional changes, keep it simple

## Dependencies / Assumptions
- FFmpeg must be installed on the system
- CUDA GPU available (with CPU fallback)
- XTTS v2 model auto-downloads on first run (~2.1 GB)

## Outstanding Questions

### Deferred to Planning
- (Affects R1-R8, Technical) Exact file structure for the FastAPI backend (single file vs modular)
- (Affects R9-R13, Technical) Whether to simplify the frontend since it only has one feature (no tab navigation needed)

## Next Steps
→ `/ce:plan` for structured implementation planning
