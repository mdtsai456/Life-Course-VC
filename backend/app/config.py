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
