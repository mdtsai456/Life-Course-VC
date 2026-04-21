import asyncio
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager, suppress

os.environ["COQUI_TOS_AGREED"] = "1"  # must precede TTS import
# Numba cannot pick a disk cache locator for code under site-packages (e.g. librosa);
# use the container-managed writable cache dir (override via env when needed).
os.environ.setdefault("NUMBA_CACHE_DIR", "/cache/numba-cache")

from app.logging_config import configure_logging

configure_logging()

import torch
from TTS.api import TTS
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.cleanup import cleanup_expired_jobs, cleanup_loop
from app.config import (
    get_cleanup_interval_seconds,
    get_cors_allowed_origins,
    get_health_rate_limit,
    get_job_ttl_seconds,
    get_storage_root,
    is_docs_enabled,
    is_rate_limit_enabled,
)
from app.constants import MAX_XTTS_PENDING
from app.rate_limit import limiter
from app.request_context import request_id_var
from app.routes.jobs import router as jobs_router
from app.routes.voice import router as voice_router

logger = logging.getLogger(__name__)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


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

    # Start background cleanup of expired job artifacts.
    storage_root = get_storage_root()
    ttl = get_job_ttl_seconds()
    interval = get_cleanup_interval_seconds()
    try:
        removed = await cleanup_expired_jobs(storage_root, ttl)
        if removed:
            logger.info("startup cleanup removed %d expired job dir(s)", removed)
    except Exception:
        logger.exception("startup cleanup failed")
    cleanup_task = asyncio.create_task(cleanup_loop(storage_root, ttl, interval))
    app.state.cleanup_task = cleanup_task

    yield

    # Teardown
    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    del app.state.cleanup_task
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

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=429,
        content={"detail": "請求過於頻繁，請稍後再試。"},
    )
    current_limit = getattr(request.state, "view_rate_limit", None)
    if current_limit is not None:
        response = request.app.state.limiter._inject_headers(response, current_limit)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming_request_id = request.headers.get("X-Request-ID", "")
    rid = incoming_request_id if _REQUEST_ID_RE.fullmatch(incoming_request_id) else str(uuid.uuid4())
    token = request_id_var.set(rid)
    request.state.request_id = rid
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    return response


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
app.include_router(jobs_router)


_health_limit = get_health_rate_limit()
_rate_limit_enabled = is_rate_limit_enabled()


if _rate_limit_enabled:
    @app.get("/health")
    @limiter.limit(_health_limit)
    async def health(request: Request):
        checks = {
            "xtts_v2": getattr(app.state, "tts_model", None) is not None,
        }
        healthy = all(checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "loading", "checks": checks},
        )
else:
    @app.get("/health")
    async def health(request: Request):
        checks = {
            "xtts_v2": getattr(app.state, "tts_model", None) is not None,
        }
        healthy = all(checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={"status": "ok" if healthy else "loading", "checks": checks},
        )
