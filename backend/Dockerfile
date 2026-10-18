# SolarPilot Backend (FastAPI). Multi-Arch: amd64 + arm64 (Raspberry Pi 4/5).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOLARPILOT_DATA_DIR=/data \
    SOLARPILOT_CONFIG_DIR=/app/config

WORKDIR /app
COPY backend/pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install . && rm -rf app

COPY backend/app ./app
COPY config ./config

RUN useradd --system --uid 10001 --home /app solarpilot \
    && mkdir -p /data && chown solarpilot /data
USER solarpilot
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
