"""Versioning regression — TC-BUG-VER-001.

Footer version must come from `/api/site/config.app_version` (single source
of truth in `js/init.js:286`), not be hardcoded in HTML.
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page, expect


def test_site_config_exposes_app_version(base_url: str):
    """`/api/site/config` returns a non-empty `app_version` string."""
    r = httpx.get(f"{base_url}/api/site/config")
    r.raise_for_status()
    version = r.json()["app_version"]
    assert isinstance(version, str) and version.strip(), \
        f"app_version must be a non-empty string: {version!r}"


def test_footer_version_matches_api_app_version(page: Page, base_url: str):
    """TC-BUG-VER-001: footer version equals `/api/site/config.app_version`.

    Strict equality with the API source-of-truth — catches any new hardcoding,
    not just the original `v2.1.0`.
    """
    api_version = httpx.get(f"{base_url}/api/site/config").json()["app_version"]
    page.goto("/")
    page.wait_for_load_state("networkidle")
    expect(page.locator(".footer-version").first).to_have_text(f"v{api_version}")
