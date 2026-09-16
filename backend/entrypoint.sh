#!/bin/sh
set -e

echo "[entrypoint] Running database migrations…"
alembic upgrade head

echo "[entrypoint] Starting Uvicorn with --reload on :8000…"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app/app \
    --log-config /app/logging.json
