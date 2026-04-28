"""Landing (этап 0 funnel — F-LND-1..5, U-LND-1, C-LND-1..3).

Public landing page rendering, headers, content guarantees.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.messages import PII, Brand, t
from tests.pages.tree_page import TreePage


def test_landing_title_has_brand(page: Page):
    """F-LND-2: title contains a brand fragment.

    Title is finalised by `_bootstrapSiteConfig` (js/init.js) after fetching
    /api/site/config — wait for `networkidle` so JS bootstrap completed.
    """
    page.goto("/")
    page.wait_for_load_state("networkidle")
    title = page.title()
    fragments = t(Brand.TITLE_FRAGMENTS)
    assert title and any(f in title for f in fragments), \
        f"title {title!r} missing any of {fragments}"


def test_landing_no_console_errors(page: Page):
    """N-1: no JS exceptions on landing; only allowlisted 401-on-anon network errors.

    Two channels are tracked separately:
      - `pageerror`: uncaught JS exceptions — must be empty.
      - `response`: 4xx/5xx network responses — 401s on known anon-rejected
        endpoints are allowlisted by URL (browser console error text alone
        does not include the URL).
    """
    js_errors: list[str] = []
    bad_responses: list[tuple[str, int]] = []

    EXPECTED_401_URLS = ("/api/account/me", "/api/auth/me", "/api/tree")

    page.on("pageerror", lambda exc: js_errors.append(str(exc)))

    def _on_response(resp):
        if resp.status >= 400 and resp.status != 404:  # 404 covered by static-assets test
            url = resp.url
            if resp.status == 401 and any(u in url for u in EXPECTED_401_URLS):
                return
            bad_responses.append((url, resp.status))

    page.on("response", _on_response)

    page.goto("/")
    page.wait_for_load_state("networkidle")

    assert not js_errors, f"JS pageerrors on landing: {js_errors}"
    assert not bad_responses, f"unexpected network errors: {bad_responses}"


def test_landing_has_main_tabs(page: Page):
    """U-LND-1: guest-visible tabs are present.

    Guests see only `tree` and `about`; map/sources/timeline are auth-gated
    by `updateGuestUI()` in index.html.
    """
    tree = TreePage(page).goto()
    page.wait_for_load_state("networkidle")
    expect(tree.tab_tree).to_be_visible()
    expect(tree.tab_about).to_be_visible()


def test_landing_no_personal_owner_data(page: Page):
    """C-LND-3: public landing must not leak owner family names (PII).

    Was xfailed under BUG-COPY-001 until upstream commit `fc2849e`
    ("fix(landing): clear inline owner PII from index.html") landed in
    dev on 28.04. Now a regular regression — the page MUST stay clean
    of any owner family names (`PII.OWNER_FAMILY_NAMES`).
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    body = page.content()
    for needle in PII.OWNER_FAMILY_NAMES:
        assert needle not in body, f"PII leak: '{needle}' visible on /"


def test_static_assets_load(page: Page):
    """F-LND-5: critical CSS/JS bundles return 200."""
    statuses: dict[str, int] = {}

    def _track(response):
        url = response.url
        if any(seg in url for seg in ("/css/", "/js/", "/assets/", "/fonts/")):
            statuses[url] = response.status

    page.on("response", _track)
    page.goto("/")
    page.wait_for_load_state("networkidle")

    bad = {url: status for url, status in statuses.items() if status >= 400}
    assert not bad, f"static assets returned errors: {bad}"
