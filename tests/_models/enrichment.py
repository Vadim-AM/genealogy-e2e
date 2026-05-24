"""Pydantic models for enrichment (AI) API contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EnrichStartResponse(BaseModel, extra="allow"):
    """Response from POST /api/enrich/{pid}."""

    job_id: str


class EnrichJobResponse(BaseModel, extra="allow"):
    """Response from GET /api/enrich/jobs/{job_id}."""

    status: str
    output: dict[str, Any] | None = None
    enrichment_id: int | None = None


class EnrichHistoryResponse(BaseModel, extra="allow"):
    """Response from GET /api/enrich/{pid}/history."""

    items: list[dict[str, Any]]
