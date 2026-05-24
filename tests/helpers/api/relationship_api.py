"""Typed wrappers for relationship API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests._core import api_paths as routes
from tests._core.response import expect_response
from tests._models.person import RelationshipResponse

if TYPE_CHECKING:
    import httpx


def get_relationships(api: httpx.Client) -> list[RelationshipResponse]:
    """GET /api/relationships → list of RelationshipResponse."""
    r = api.get(routes.RELATIONSHIPS)
    return expect_response(r, label="relationships").status_ok().list_schema(RelationshipResponse)


def create_relationship(api: httpx.Client, *, rel_type: str, person1_id: str, person2_id: str) -> None:
    """POST /api/relationships → assert 2xx."""
    r = api.post(routes.RELATIONSHIPS, json={
        "type": rel_type,
        "person1_id": person1_id,
        "person2_id": person2_id,
    })
    expect_response(r, label="create relationship").status_ok()


def delete_relationship(api: httpx.Client, rel_id: str | int) -> None:
    """DELETE /api/relationships/{id} → assert 2xx."""
    r = api.delete(routes.relationship(str(rel_id)))
    expect_response(r, label=f"delete relationship {rel_id}").status_ok()
