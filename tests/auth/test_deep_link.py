"""Deep-link routing — TC-AUTH-1."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from framework.step import step
from helpers.auth.auth_ui import wait_for_auth_state
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData


@allure.title("Прямая ссылка на персону сохраняет авторизацию")
def test_deep_link_to_demo_self_preserves_auth(owner_page: Page) -> None:
    """TC-AUTH-1: переход на /#/p/demo-self сохраняет авторизацию."""
    with step("действие: переход по прямой ссылке на персону"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

    with step("проверка: профиль отрисован и авторизация сохранена"):
        expect(panel.title, ErrMsg.wrong_text_content).not_to_have_text("")
        expect(panel.container, ErrMsg.profile_not_visible).to_be_visible()

        wait_for_auth_state(owner_page, expected=True)


@allure.title("Ссылка на несуществующую персону не сбрасывает авторизацию")
def test_deep_link_to_unknown_id_keeps_auth(owner_page: Page) -> None:
    """Ссылка на несуществующую персону не сбрасывает авторизацию."""
    with step("действие: переход по ссылке на несуществующую персону"):
        tree = TreePage(owner_page)
        tree.goto_hash("#/p/no-such-person")

    with step("проверка: вкладка дерева видна и авторизация сохранена"):
        expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()
        wait_for_auth_state(owner_page, expected=True)
