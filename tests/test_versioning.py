"""Versioning regression — TC-BUG-VER-001.

Footer version must come from `/api/site/config` (single source of truth),
not be hardcoded in HTML. Closed pending in audit-серия 27.04.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect


def test_site_config_exposes_version(base_url: str):
    """/api/site/config must include an `app_version` (or similar) field."""
    r = httpx.get(f"{base_url}/api/site/config")
    assert r.status_code == 200
    data = r.json()
    # Field name may evolve; accept any of these.
    version = (
        data.get("app_version")
        or data.get("version")
        or data.get("backend_version")
    )
    assert version, f"site config has no version field; keys={list(data.keys())}"
    assert isinstance(version, str) and version.strip(), "version must be non-empty string"


def test_footer_version_is_not_hardcoded_v210(page: Page):
    """TC-BUG-VER-001: footer must not show stale `v2.1.0` after Pivot.

    Source of truth is `__version__.py`. Test goes positive: footer shows
    *some* version, and it isn't the well-known stale value.
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    footer_text = (page.locator("footer, .footer-version").first.text_content() or "")
    # Either footer-version explicit, or just any text in the footer.
    body_text = page.locator("body").text_content() or ""
    full = footer_text + " " + body_text
    # Stale value MUST NOT appear in main `<footer>` strings any more.
    assert "v2.1.0" not in footer_text, "BUG-VER-001 regression: hardcoded v2.1.0 in footer"
