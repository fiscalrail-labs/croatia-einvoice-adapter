#!/bin/sh
set -eu

BASE_URL=${1:-http://127.0.0.1:8000}
API_KEY=${2:-${DIRECT_API_KEY:-}}

if [ -z "$API_KEY" ]; then
  echo "Usage: $0 BASE_URL API_KEY" >&2
  exit 2
fi

curl -fsS "$BASE_URL/health"
printf '\n'
curl -fsS "$BASE_URL/v1/hr/invoices/preflight" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $API_KEY" \
  --data-binary @examples/invoice.json
printf '\n'
