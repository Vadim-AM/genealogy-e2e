"""Enrichment domain fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from api import routes

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.fixture
def enrich_post_spy(owner_page: Page) -> list[str]:
    """Подписывается на POST /api/enrich/* и собирает URL вызовов."""
    calls: list[str] = []
    owner_page.on(
        "request",
        lambda req: calls.append(req.url)
        if req.method == "POST" and routes.ENRICH_PREFIX in req.url
        else None,
    )
    return calls
