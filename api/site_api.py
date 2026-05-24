"""Typed wrappers for site config, sharing, and sources API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api import routes
from framework.response import expect_response
from models.site import (
    ShareCreateResponse,
    SiteConfigResponse,
    SourceResponse,
)

if TYPE_CHECKING:
    import httpx


def get_site_config(api: httpx.Client) -> SiteConfigResponse:
    """GET /api/site/config → validated SiteConfigResponse."""
    r = api.get(routes.SITE_CONFIG)
    return expect_response(r, label="site config").status_ok().schema(SiteConfigResponse)


def patch_site_config(api: httpx.Client, **fields: object) -> SiteConfigResponse:
    """PATCH /api/site/config → validated SiteConfigResponse."""
    r = api.patch(routes.SITE_CONFIG, json=fields)
    return expect_response(r, label="patch site config").status_ok().schema(SiteConfigResponse)


def create_share(api: httpx.Client, person_id: str) -> ShareCreateResponse:
    """POST /api/share/create → validated ShareCreateResponse."""
    r = api.post(routes.SHARE_CREATE, json={"scope": "person", "person_id": person_id})
    return expect_response(r, label="create share").status_ok().schema(ShareCreateResponse)


def create_source(api: httpx.Client, *, name: str, source_type: str = "document") -> SourceResponse:
    """POST /api/sources → validated SourceResponse."""
    r = api.post(routes.SOURCES, json={"name": name, "type": source_type})
    return expect_response(r, label="create source").status_ok().schema(SourceResponse)


def get_sources(api: httpx.Client) -> list[SourceResponse]:
    """GET /api/sources → list of SourceResponse."""
    r = api.get(routes.SOURCES)
    return expect_response(r, label="list sources").status_ok().list_schema(SourceResponse)
