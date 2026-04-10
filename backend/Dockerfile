# syntax=docker/dockerfile:1
# GPU: official PyTorch CUDA runtime (see https://hub.docker.com/r/pytorch/pytorch/tags).
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime AS runtime-gpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appuser && useradd --system --no-create-home --ingroup appuser appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY app ./app

RUN chown -R appuser:appuser /app /docker-entrypoint.sh
USER appuser

ENTRYPOINT ["/docker-entrypoint.sh"]

# CPU: slim Python + PyTorch CPU wheels
FROM python:3.12-slim-bookworm AS runtime-cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appuser && useradd --system --no-create-home --ingroup appuser appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY app ./app

RUN chown -R appuser:appuser /app /docker-entrypoint.sh
USER appuser

ENTRYPOINT ["/docker-entrypoint.sh"]
