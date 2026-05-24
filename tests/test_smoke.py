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
from tests.pages.signup_page import SignupPage
from tests.pages.tree_page import TreePage
from tests.pages.wait_page import WaitPage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@pytest.mark.smoke
@allure.title("Smoke: главная страница загружается и показывает заголовок")
def test_landing_loads(page: Page, anon_pages: PageFactory):
    """F-LND-1/2: GET / → 200, HTML, title contains brand."""
    tree = anon_pages.navigate_to(TreePage)
    expect(page).not_to_have_url("about:blank")
    expect(tree.h1).to_be_visible()


@pytest.mark.smoke
@allure.title("Smoke: форма регистрации отображается со всеми полями")
def test_signup_form_visible(anon_pages: PageFactory):
    """F-SU-1: /signup renders form with required inputs."""
    signup = anon_pages.navigate_to(SignupPage)
    signup.expect_visible_form()


@pytest.mark.smoke
@allure.title("Smoke: форма вейтлиста отображается на /wait")
def test_wait_form_visible(anon_pages: PageFactory):
    """C-LND-1 + waitlist scope: /wait renders form."""
    wait = anon_pages.navigate_to(WaitPage)
    wait.expect_visible_form()


@pytest.mark.smoke
@allure.title("Smoke: /api/health доступен через браузер и отвечает 200")
def test_health_endpoint_via_browser(page: Page):
    """Sanity: even page.goto sees the live FastAPI subprocess."""
    response = page.goto(API.HEALTH)
    assert response is not None, "page.goto(/api/health) returned None"
    assert response.status == 200, (
        f"/api/health returned {response.status}, backend may be down"
    )
