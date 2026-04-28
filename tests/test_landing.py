"""Landing (этап 0 funnel — F-LND-1..5, U-LND-1, C-LND-1..3).

Public landing page rendering, headers, content guarantees.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from tests.pages.tree_page import TreePage


def test_landing_returns_200_with_html(page: Page):
    """F-LND-1: GET / → 200 + HTML."""
    response = page.goto("/")
    assert response is not None
    assert response.status == 200
    assert "text/html" in (response.headers.get("content-type") or "")


def test_landing_title_has_brand(page: Page):
    """F-LND-2: title contains brand. Title is finalised by `_bootstrapSiteConfig`
    in js/init.js after fetching /api/site/config, so wait for networkidle."""
    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)
    title = page.title()
    assert title and len(title) > 0, "document.title is empty"
    assert any(token in title for token in ("Родословн", "Семейн", "древо")), title


def test_landing_no_console_errors(page: Page):
    """N-1: 0 fatal console errors on landing.

    401 from /api/account/me / /api/auth/me are expected for anonymous
    visitors — those are filtered. We assert that no JS exceptions or
    truly broken endpoints leak into console.
    """
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)

    def _is_noise(line: str) -> bool:
        low = line.lower()
        # Expected: anon hits authed-only endpoints → 401 (auth/me, tree, etc.)
        if "401" in line or "unauthorized" in low:
            return True
        if "favicon" in low:
            return True
        return False

    fatal = [e for e in errors if not _is_noise(e)]
    assert not fatal, f"fatal console errors: {fatal}"


def test_landing_has_main_tabs(page: Page, soft_check):
    """U-LND-1 + tab structure: guest-visible tabs are present.

    Guests see only `tree` and `about`; map/sources/timeline are auth-gated
    by `updateGuestUI()` in index.html (see line 332).
    """
    tree = TreePage(page).goto()
    page.wait_for_load_state("networkidle", timeout=10_000)
    tree.soft_check_guest_tabs(soft_check)


@pytest.mark.xfail(
    reason="BUG-MT-001 / BUG-COPY-001: js/constants.js + global site_config "
           "содержат 'Данилюк/Макаров' (см. docs/test-plan.md). Фикс готов "
           "локально, не влит. Снять xfail после merge.",
    strict=False,
)
def test_landing_no_personal_owner_data(page: Page):
    """C-LND-3: public landing must not leak Данилюк/Макаров (PII)."""
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    body = page.content()
    for needle in ("Данилюк", "Макаров"):
        assert needle not in body, f"PII leak: '{needle}' visible on /"


def test_static_assets_load(page: Page, soft_check):
    """F-LND-5: critical CSS/JS bundles return 200."""
    statuses: dict[str, int] = {}

    def _track(response):
        url = response.url
        if any(seg in url for seg in ("/css/", "/js/", "/assets/", "/fonts/")):
            statuses[url] = response.status

    page.on("response", _track)
    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)

    bad = {url: status for url, status in statuses.items() if status >= 400}
    assert not bad, f"static assets returned errors: {bad}"
