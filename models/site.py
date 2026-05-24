"""Pydantic models for site config and sharing API contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SiteConfigResponse(BaseModel, extra="allow"):
    """Response from GET /api/site/config."""

    site_name: str | None = None
    app_version: str | None = None


class ShareCreateResponse(BaseModel, extra="allow"):
    """Response from POST /api/share/create."""

    id: int
    url: str


class ShareListItem(BaseModel, extra="allow"):
    """Single item in GET /api/share/list."""

    id: int


class ShareListResponse(BaseModel, extra="allow"):
    """Response from GET /api/share/list."""

    items: list[ShareListItem]


class SourceResponse(BaseModel, extra="allow"):
    """Response from POST /api/sources and linked-source list items."""

    id: str | None = None
    source_id: str | None = None
    name: str
    type: str | None = None


class SubscriptionResponse(BaseModel, extra="allow"):
    """Response from GET /api/subscription/current."""

    tenant: dict[str, Any] | None = None
    subscription: dict[str, Any] | None = None


class RetentionOfferStatus(BaseModel, extra="allow"):
    """Response from GET /api/tenant/retention-offer-status."""

    show: bool


class RetentionOfferApply(BaseModel, extra="allow"):
    """Response from POST /api/tenant/retention-offer/apply."""

    coupon_code: str
    discount_percent: int | None = None
