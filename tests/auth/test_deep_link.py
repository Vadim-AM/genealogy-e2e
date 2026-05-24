"""Deep-link routing — TC-AUTH-1."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from framework.step import step
from helpers.auth.auth_ui import wait_for_auth_state
from src.texts import ErrMsg, TestData


@allure.title("Прямая ссылка на персону сохраняет авторизацию")
def test_deep_link_to_demo_self_preserves_auth(owner_page: Page) -> None:
    """TC-AUTH-1: переход на /#/p/demo-self сохраняет авторизацию."""
    with step("действие: переход по прямой ссылке на персону"):
        owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: профиль отрисован и авторизация сохранена"):
        # no semantic: layout container
        expect(owner_page.locator("#tab-tree .section-title"), ErrMsg.wrong_text_content).not_to_have_text("")
        # no semantic: data-testid element, no role
        expect(owner_page.locator('[data-testid="profile-page"]'), ErrMsg.profile_not_visible).to_be_visible()

        wait_for_auth_state(owner_page, expected=True)


@allure.title("Ссылка на несуществующую персону не сбрасывает авторизацию")
def test_deep_link_to_unknown_id_keeps_auth(owner_page: Page) -> None:
    """Ссылка на несуществующую персону не сбрасывает авторизацию."""
    with step("действие: переход по ссылке на несуществующую персону"):
        owner_page.goto("/#/p/no-such-person")
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: вкладка дерева видна и авторизация сохранена"):
        expect(owner_page.locator('[data-tab="tree"]'), ErrMsg.tab_not_visible).to_be_visible()
        wait_for_auth_state(owner_page, expected=True)
