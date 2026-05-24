"""Typed wrappers for platform admin API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from api import routes
from framework.response import expect_response
from models.platform import (
    AuditLogResponse,
    FeaturesResponse,
    PlatformSettingsResponse,
    TelemetryResponse,
)

if TYPE_CHECKING:
    import httpx


def get_features(base_url: str) -> FeaturesResponse:
    """GET /api/config/features (public, no auth) → FeaturesResponse."""
    import httpx as _httpx


    r = _httpx.get(f"{base_url}{routes.CONFIG_FEATURES}")
    return expect_response(r, label="config features").status_ok().schema(FeaturesResponse)


def get_platform_settings(api: httpx.Client) -> PlatformSettingsResponse:
    """GET /api/platform/settings → PlatformSettingsResponse."""
    r = api.get(routes.PLATFORM_SETTINGS)
    return expect_response(r, label="platform settings").status_ok().schema(PlatformSettingsResponse)


def get_audit_log(api: httpx.Client, **params: Any) -> AuditLogResponse:
    """GET /api/platform/audit-log → AuditLogResponse."""
    r = api.get(routes.PLATFORM_AUDIT_LOG, params=params)
    return expect_response(r, label="audit log").status_ok().schema(AuditLogResponse)


def post_telemetry(api: httpx.Client, batch: list[dict]) -> TelemetryResponse:
    """POST /api/telemetry/events → TelemetryResponse."""
    r = api.post(routes.TELEMETRY_EVENTS, json={"batch": batch})
    return expect_response(r, label="telemetry").status_ok().schema(TelemetryResponse)
