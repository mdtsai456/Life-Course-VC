"""Logging configuration with request_id injection."""

from __future__ import annotations

import logging
import logging.config
import os
import sys


def configure_logging() -> None:
    raw_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    get_level_names_mapping = getattr(logging, "getLevelNamesMapping", None)
    valid_levels = (
        set(get_level_names_mapping())
        if callable(get_level_names_mapping)
        else set(logging._nameToLevel)
    )
    level = raw_level if raw_level in valid_levels else "INFO"
    if raw_level != level:
        print(f"Invalid LOG_LEVEL={raw_level!r}; falling back to INFO", file=sys.stderr)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "app.request_context.RequestIdFilter",
            },
        },
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id"],
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": level, "propagate": False},
        },
        "root": {"handlers": ["default"], "level": level},
    })
