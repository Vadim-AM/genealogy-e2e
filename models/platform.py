"""Pydantic models for platform admin API contracts."""

from __future__ import annotations

from pydantic import BaseModel


class FeaturesResponse(BaseModel, extra="allow"):
    """Response from GET /api/config/features."""

    ai_search_enabled: bool


class PlatformSettingsResponse(BaseModel, extra="allow"):
    """Response from GET /api/platform/settings."""

    enable_ai_search: bool | None = None


class AuditLogItem(BaseModel, extra="allow"):
    """Single item in GET /api/platform/audit-log."""

    action: str | None = None
    ip_hash: str | None = None


class AuditLogResponse(BaseModel, extra="allow"):
    """Response from GET /api/platform/audit-log."""

    items: list[AuditLogItem]


class TenantOverrideItem(BaseModel, extra="allow"):
    """Single override in GET /api/platform/tenant-overrides/{slug}."""

    field_name: str | None = None


class CheckoutResponse(BaseModel, extra="allow"):
    """Response from POST /api/subscription/checkout."""

    status: str


class TelemetryResponse(BaseModel, extra="allow"):
    """Response from POST /api/telemetry/events."""

    received: int
