"""UI domain fixtures — viewport-specific page factories."""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from tests.helpers.ui.viewport import make_page


@pytest.fixture
def mobile_page(browser: Browser, base_url: str) -> Iterator[Page]:
    """iPhone SE viewport — anonymous (no cookies)."""
    yield from make_page(browser, base_url, w=375, h=812)


@pytest.fixture
def tablet_owner_page(
    browser: Browser, base_url: str, owner_user
) -> Iterator[Page]:
    """iPad portrait viewport with owner_user cookies + tenant header."""
    ctx = browser.new_context(
        base_url=base_url,
        viewport={"width": 768, "height": 1024},
        ignore_https_errors=True,
        extra_http_headers={"X-Tenant-Slug": owner_user.slug},
    )
    for name, value in owner_user.cookies.items():
        ctx.add_cookies([{"name": name, "value": value, "url": base_url}])
    ctx.add_init_script(
        "try { localStorage.setItem('v1', '1'); "
        "localStorage.setItem('genealogy_tour_v1', '1'); } catch (e) {}"
    )
    page = ctx.new_page()
    yield page
    ctx.close()
