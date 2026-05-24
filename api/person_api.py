"""Typed wrappers for person/tree API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api import routes
from framework.response import expect_response
from models.person import PersonCreate, PersonResponse, TreeResponse

if TYPE_CHECKING:
    import httpx


def get_tree(api: httpx.Client) -> TreeResponse:
    """GET /api/tree → validated TreeResponse."""
    r = api.get(routes.TREE)
    return expect_response(r, label="GET tree").status_ok().schema(TreeResponse)


def get_people(api: httpx.Client) -> list[PersonResponse]:
    """GET /api/tree → list of PersonResponse."""
    return get_tree(api).people


def get_people_count(api: httpx.Client) -> int:
    """Return the count of people in the tree."""
    return len(get_people(api))


def create_person(api: httpx.Client, data: PersonCreate) -> PersonResponse:
    """POST /api/people → validated PersonResponse."""
    r = api.post(routes.PEOPLE, json=data.model_dump(exclude_none=True))
    return expect_response(r, label="create person").status_ok().schema(PersonResponse)


def patch_person(api: httpx.Client, pid: str, **fields: object) -> PersonResponse:
    """PATCH /api/people/{pid} → validated PersonResponse."""
    r = api.patch(routes.person(pid), json=fields)
    return expect_response(r, label=f"patch person {pid}").status_ok().schema(PersonResponse)


def delete_person(api: httpx.Client, pid: str) -> None:
    """DELETE /api/people/{pid} → assert 2xx."""
    r = api.delete(routes.person(pid))
    expect_response(r, label=f"delete person {pid}").status_ok()
