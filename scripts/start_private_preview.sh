#!/bin/sh
set -eu

PORT=${PORT:-8000}
KEY=${DIRECT_API_KEY:-$(python -c 'import secrets; print(secrets.token_urlsafe(32))')}

cat <<MSG
Private preview starting.
Base URL: http://127.0.0.1:${PORT}
Docs: http://127.0.0.1:${PORT}/docs
X-API-Key: ${KEY}

This is a development preview and returns production_ready=false.
MSG

exec env \
  APP_ENV=production \
  ALLOW_UNAUTHENTICATED=false \
  DIRECT_API_KEY="$KEY" \
  uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
