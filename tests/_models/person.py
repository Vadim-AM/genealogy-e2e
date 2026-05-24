"""Pydantic models for person and tree API contracts."""

from __future__ import annotations

from pydantic import BaseModel


class PersonCreate(BaseModel):
    """Request body for POST /api/people."""

    id: str
    name: str
    branch: str = "paternal"
    gender: str = "m"
    summary: str | None = None
    notes: str | None = None
    birth: str | None = None
    birth_place: str | None = None
    death: str | None = None
    badge: str | None = None
    maiden_name: str | None = None
    patronymic: str | None = None
    status: str | None = None


class PersonResponse(BaseModel, extra="allow"):
    """Response from GET /api/people/{id} and items in TreeResponse.people."""

    id: str
    name: str
    branch: str | None = None
    gender: str | None = None
    summary: str | None = None
    display_slug: str | None = None


class RelationshipResponse(BaseModel, extra="allow"):
    """Single relationship in GET /api/relationships."""

    id: str | int | None = None
    type: str
    person1_id: str
    person2_id: str


class TreeResponse(BaseModel, extra="allow"):
    """Response from GET /api/tree."""

    people: list[PersonResponse]


class LocationResponse(BaseModel, extra="allow"):
    """Single location in GET /api/locations."""

    id: str | int
    name: str
    lat: float | None = None
    lng: float | None = None
    type: str | None = None
