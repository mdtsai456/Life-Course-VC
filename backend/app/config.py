import os


def get_cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def is_docs_enabled() -> bool:
    return os.getenv("DOCS_ENABLED", "true").strip().lower() in ("true", "1", "yes")
