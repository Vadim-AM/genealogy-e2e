"""Versioning regression — TC-BUG-VER-001.

Footer version must come from `/api/site/config.app_version` (single source
of truth in `js/init.js:286`), not be hardcoded in HTML.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.err_msg import ErrMsg
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests._models.site import SiteConfigResponse
from tests.pages.tree_page import TreePage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@allure.title("Конфиг сайта содержит непустую версию приложения")
def test_site_config_exposes_app_version(base_url: str):
    """`/api/site/config` returns a non-empty `app_version` string."""
    r = httpx.get(f"{base_url}{API.SITE_CONFIG}", timeout=TIMEOUTS.api_request)
    config = expect_response(r, label="GET /api/site/config").status_ok().schema(SiteConfigResponse)
    assert isinstance(config.app_version, str) and config.app_version.strip(), \
        f"app_version must be a non-empty string: {config.app_version!r}"


@allure.title("Версия в футере совпадает с версией из API")
def test_footer_version_matches_api_app_version(page: Page, base_url: str, anon_pages: PageFactory):
    """TC-BUG-VER-001: footer version equals `/api/site/config.app_version`.

    Strict equality with the API source-of-truth — catches any new hardcoding,
    not just the original `v2.1.0`.
    """
    with step("подготовка: получить версию из API"):
        r = httpx.get(f"{base_url}{API.SITE_CONFIG}", timeout=TIMEOUTS.api_request)
        config = expect_response(r, label="GET /api/site/config").status_ok().schema(SiteConfigResponse)
        api_version = config.app_version

    with step("проверка: футер показывает ту же версию"):
        _ = anon_pages.navigate_to(TreePage)
        # no semantic: version stamp, no ARIA
        expect(
            page.locator('[data-testid="footer-version"]').first,
            ErrMsg.wrong_text_content,
        ).to_have_text(f"v{api_version}")
