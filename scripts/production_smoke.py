from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
api_key = os.environ.get("API_KEY", "integration-test-secret")
root = Path(__file__).resolve().parents[1]


def get(path: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(base + path, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def post(path: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        base + path,
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


status, ready = get("/ready")
assert status == 200 and ready["production_ready"] is True, ready
payload = json.loads((root / "examples" / "invoice.json").read_text())
status, result = post("/v1/hr/invoices/preflight", payload)
assert status == 200, result
assert result["validation"]["production_ready"] is True, result["validation"]
assert result["validation"]["valid"] is True, result["validation"]
print(json.dumps({"ready": ready, "validation_summary": result["validation"]["summary"]}, indent=2))
