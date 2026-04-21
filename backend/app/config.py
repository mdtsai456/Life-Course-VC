import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return os.getenv("ENV", "").strip().lower() in ("production", "prod")


def get_cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if _is_production() and any("localhost" in o for o in origins):
        logger.warning("CORS_ALLOWED_ORIGINS contains localhost in production environment")
    return origins


def is_docs_enabled() -> bool:
    default = "false" if _is_production() else "true"
    return os.getenv("DOCS_ENABLED", default).strip().lower() in ("true", "1", "yes")


_BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


def get_storage_root() -> Path:
    return Path(os.getenv("STORAGE_ROOT", str(_BASE_DIR / "storage"))).resolve()


def get_job_ttl_seconds() -> int:
    try:
        days = float(os.getenv("JOB_TTL_DAYS", "7"))
    except ValueError:
        days = 7.0
    return int(max(0.0, days) * 86400)


def get_cleanup_interval_seconds() -> int:
    try:
        hours = float(os.getenv("JOB_CLEANUP_INTERVAL_HOURS", "6"))
    except ValueError:
        hours = 6.0
    return int(max(0.1, hours) * 3600)


def get_clone_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_CLONE", "10/minute").strip()


def get_health_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_HEALTH", "60/minute").strip()


def is_rate_limit_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in ("true", "1", "yes")
