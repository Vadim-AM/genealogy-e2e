"""UI domain fixtures — viewport-specific page factories."""
from __future__ import annotations

from collections.abc import Iterator

import allure
import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from tests.helpers.ui.viewport import make_page


@pytest.fixture
def mobile_page(request, browser: Browser, base_url: str) -> Iterator[Page]:
    """iPhone SE viewport — anonymous (no cookies)."""
    gen = make_page(browser, base_url, w=375, h=812)
    page = next(gen)
    request.node._pw_page = page
    try:
        yield page
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.fixture
def tablet_owner_page(
    request, browser: Browser, base_url: str, owner_user, tmp_path
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
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = ctx.new_page()
    request.node._pw_page = page
    yield page

    failed = getattr(getattr(request.node, "rep_call", None), "failed", False)
    if failed:
        trace_path = tmp_path / "trace-tablet.zip"
        try:
            ctx.tracing.stop(path=str(trace_path))
        except Exception:
            trace_path = None
        if trace_path and trace_path.exists():
            allure.attach.file(
                str(trace_path),
                name="playwright-trace-tablet.zip",
                extension="zip",
            )
    else:
        try:
            ctx.tracing.stop()
        except Exception:
            pass
    ctx.close()
