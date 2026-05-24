"""Smoke tests — verify the e2e infrastructure boots and basic pages render.

These are the canary for the whole suite: if these fail, conftest fixtures
(uvicorn subprocess, AI mock, reset endpoint, Page Objects) need fixing
before bothering with the rest.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import pytest
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.err_msg import ErrMsg
from tests._core.step import step
from tests.pages.signup_page import SignupPage
from tests.pages.tree_page import TreePage
from tests.pages.wait_page import WaitPage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@pytest.mark.smoke
@allure.title("Smoke: главная страница загружается и показывает заголовок")
def test_landing_loads(page: Page, anon_pages: PageFactory):
    """F-LND-1/2: GET / → 200, HTML, title contains brand."""
    with step("действие: загрузить главную"):
        tree = anon_pages.navigate_to(TreePage)

    with step("проверка: страница загрузилась и заголовок виден"):
        expect(page, ErrMsg.url_wrong).not_to_have_url("about:blank")
        expect(tree.h1, ErrMsg.tree_not_rendered).to_be_visible()


@pytest.mark.smoke
@allure.title("Smoke: форма регистрации отображается со всеми полями")
def test_signup_form_visible(anon_pages: PageFactory):
    """F-SU-1: /signup renders form with required inputs."""
    with step("действие: открыть signup"):
        signup = anon_pages.navigate_to(SignupPage)

    with step("проверка: форма отображается со всеми полями"):
        signup.expect_visible_form()


@pytest.mark.smoke
@allure.title("Smoke: форма вейтлиста отображается на /wait")
def test_wait_form_visible(anon_pages: PageFactory):
    """C-LND-1 + waitlist scope: /wait renders form."""
    with step("действие: открыть /wait"):
        wait = anon_pages.navigate_to(WaitPage)

    with step("проверка: форма вейтлиста отображается"):
        wait.expect_visible_form()


@pytest.mark.smoke
@allure.title("Smoke: /api/health доступен через браузер и отвечает 200")
def test_health_endpoint_via_browser(page: Page):
    """Sanity: even page.goto sees the live FastAPI subprocess."""
    with step("действие: запросить /api/health через браузер"):
        response = page.goto(API.HEALTH)

    with step("проверка: endpoint доступен и отвечает 200"):
        assert response is not None, "page.goto(/api/health) returned None"
        assert response.status == 200, (
            f"/api/health returned {response.status}, backend may be down"  # noqa: drift
        )
