#!/bin/sh
set -e
if [ "$(id -u)" = 0 ]; then
  mkdir -p /cache/home /cache/huggingface /cache/torch /cache/xdg /app/storage
  chown -R appuser:appuser /cache /app/storage
  exec runuser -u appuser -- uvicorn app.main:app --host 0.0.0.0 --port "${UVICORN_PORT:-8000}"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${UVICORN_PORT:-8000}"
