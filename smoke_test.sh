#!/usr/bin/env sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY_VALUE="${API_KEY:-}"
AUTH_ARGS=""
if [ -n "$API_KEY_VALUE" ]; then
  AUTH_ARGS="-H X-API-Key:$API_KEY_VALUE"
fi

curl -fsS "$BASE_URL/health"
printf '\n'
# shellcheck disable=SC2086
curl -fsS $AUTH_ARGS \
  -H 'Content-Type: application/json' \
  --data-binary @examples/invoice.json \
  "$BASE_URL/v1/hr/invoices/preflight"
printf '\n'
