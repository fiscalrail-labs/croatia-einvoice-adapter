#!/bin/sh
set -eu

DEST="${1:-/opt/fiscalrail/ubl}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$DEST"

# Croatian Tax Administration: UBL 2.1 eInvoice schemas, published 2026-04-15.
curl --fail --location --retry 4 --retry-delay 3 \
  --output "$TMP/hr-ubl.zip" \
  "https://porezna.gov.hr/fiskalizacija/api/dokumenti/198"

unzip -q "$TMP/hr-ubl.zip" -d "$DEST"
SCHEMA="$(find "$DEST" -type f -name 'UBL-Invoice-2.1.xsd' | head -n 1)"
if [ -z "$SCHEMA" ]; then
  echo "UBL-Invoice-2.1.xsd was not found in official archive" >&2
  exit 1
fi

printf '%s\n' "$SCHEMA" > "$DEST/invoice-schema.path"
sha256sum "$TMP/hr-ubl.zip" | awk '{print $1}' > "$DEST/source.sha256"
printf '%s\n' 'https://porezna.gov.hr/fiskalizacija/api/dokumenti/198' > "$DEST/source.url"
