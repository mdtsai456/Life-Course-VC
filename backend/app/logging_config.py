"""Logging configuration with request_id injection."""

from __future__ import annotations

import logging.config
import os


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()

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
