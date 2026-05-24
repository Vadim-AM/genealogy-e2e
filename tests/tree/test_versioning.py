"""Versioning regression — TC-BUG-VER-001.

Footer version must come from `/api/site/config.app_version` (single source
of truth in `js/init.js:286`), not be hardcoded in HTML.
"""

from __future__ import annotations

import allure
import httpx
from playwright.sync_api import Page, expect

from tests.response import expect_response
from tests.step import step


@allure.title("Конфиг сайта содержит непустую версию приложения")
def test_site_config_exposes_app_version(base_url: str):
    """`/api/site/config` returns a non-empty `app_version` string."""
    r = httpx.get(f"{base_url}/api/site/config")
    expect_response(r, label="GET /api/site/config").status_ok()
    version = r.json()["app_version"]
    assert isinstance(version, str) and version.strip(), \
        f"app_version must be a non-empty string: {version!r}"


@allure.title("Версия в футере совпадает с версией из API")
def test_footer_version_matches_api_app_version(page: Page, base_url: str):
    """TC-BUG-VER-001: footer version equals `/api/site/config.app_version`.

    Strict equality with the API source-of-truth — catches any new hardcoding,
    not just the original `v2.1.0`.
    """
    with step("подготовка: получить версию из API"):
        api_version = httpx.get(f"{base_url}/api/site/config").json()["app_version"]

    with step("проверка: футер показывает ту же версию"):
        page.goto("/")
        page.wait_for_load_state("domcontentloaded")
        expect(page.locator('[data-testid="footer-version"]').first).to_have_text(f"v{api_version}")
