#!/bin/sh
set -e

set -- app.main:app --host 0.0.0.0 --port "${UVICORN_PORT:-8000}" --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1,::1}"
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  set -- "$@" --reload --reload-dir /app/app --reload-exclude '/app/storage/*'
fi

if [ "$(id -u)" = 0 ]; then
  mkdir -p /cache/home /cache/huggingface /cache/torch /cache/xdg /cache/numba-cache /app/storage
  chown -R appuser:appuser /cache /app/storage
  exec gosu appuser uvicorn "$@"
fi
exec uvicorn "$@"
