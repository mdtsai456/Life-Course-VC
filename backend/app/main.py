import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

os.environ["COQUI_TOS_AGREED"] = "1"  # must precede TTS import
# Numba cannot pick a disk cache locator for code under site-packages (e.g. librosa); use a writable dir.
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba-cache")

import torch
from TTS.api import TTS
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_cors_allowed_origins, is_docs_enabled
from app.constants import MAX_XTTS_PENDING
from app.routes.voice import router as voice_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load XTTS v2 model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    start = time.monotonic()
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    elapsed = time.monotonic() - start
    logger.info("XTTS v2 model loaded in %.1fs (device: %s)", elapsed, device)
    app.state.tts_model = tts
    app.state.xtts_lock = asyncio.Lock()
    app.state.xtts_semaphore = asyncio.Semaphore(MAX_XTTS_PENDING)
    app.state.xtts_admission_lock = asyncio.Lock()

    yield

    # Teardown
    del app.state.xtts_admission_lock
    del app.state.xtts_semaphore
    del app.state.xtts_lock
    del app.state.tts_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Models unloaded")


_docs_enabled = is_docs_enabled()
app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if _docs_enabled and request.url.path in _DOCS_PATHS:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data: cdn.jsdelivr.net; frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response

app.include_router(voice_router)


@app.get("/health")
async def health():
    checks = {
        "xtts_v2": getattr(app.state, "tts_model", None) is not None,
    }
    healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "loading", "checks": checks},
    )
