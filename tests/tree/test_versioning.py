"""TC-BUG-VER-001: версия в футере совпадает с /api/site/config.app_version."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.site import SiteConfigResponse
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Конфиг сайта содержит непустую версию приложения")
def test_site_config_exposes_app_version(base_url: str) -> None:
    """app_version в /api/site/config — непустая строка."""
    r = httpx.get(f"{base_url}{routes.SITE_CONFIG}")
    config = expect_response(r, label="GET /api/site/config").status_ok().schema(SiteConfigResponse)
    should.be_true(isinstance(config.app_version, str) and config.app_version.strip(), ErrMsg.app_version_empty)


@allure.title("Версия в футере совпадает с версией из API")
def test_footer_version_matches_api_app_version(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """Версия в футере строго равна app_version из API."""
    with step("подготовка: получить версию из API"):
        r = httpx.get(f"{base_url}{routes.SITE_CONFIG}")
        config = expect_response(r, label="GET /api/site/config").status_ok().schema(SiteConfigResponse)
        api_version = config.app_version

    with step("проверка: футер показывает ту же версию"):
        tree = anon_pages.navigate_to(TreePage)
        expect(
            tree.footer_version,
            ErrMsg.wrong_text_content,
        ).to_have_text(f"v{api_version}")
