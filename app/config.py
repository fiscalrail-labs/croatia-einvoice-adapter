from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    allow_unauthenticated: bool
    direct_api_key: str | None
    rapidapi_proxy_secret: str | None
    max_request_bytes: int

    @property
    def access_is_configured(self) -> bool:
        return bool(
            self.allow_unauthenticated
            or self.direct_api_key
            or self.rapidapi_proxy_secret
        )


def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_open = app_env != "production"
    max_request_bytes = int(os.getenv("MAX_REQUEST_BYTES", "2500000"))
    if max_request_bytes < 1024:
        raise ValueError("MAX_REQUEST_BYTES must be at least 1024")

    return Settings(
        app_env=app_env,
        allow_unauthenticated=_as_bool("ALLOW_UNAUTHENTICATED", default_open),
        direct_api_key=os.getenv("DIRECT_API_KEY") or None,
        rapidapi_proxy_secret=os.getenv("RAPIDAPI_PROXY_SECRET") or None,
        max_request_bytes=max_request_bytes,
    )
