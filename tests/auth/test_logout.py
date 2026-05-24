"""Logout flow — F-LO-1..2."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from framework.step import step
from pages.login_page import LoginPage
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Клик 'Выйти' переключает индикатор в гостевой режим")
def test_owner_clicks_logout_link_and_indicator_switches_to_guest(
    owner_page: Page, owner_user, pages: PageFactory,
) -> None:
    """F-LO-1: клик по «Выйти» сбрасывает session и переключает UI в guest."""
    with step("подготовка: загрузка и проверка authed-состояния"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state(TestData.DEFAULT_FULL_NAME)

    with step("действие: выход"):
        tree.logout()

    with step("проверка: гостевой режим"):
        tree.expect_guest_state()


@allure.title("Повторный вход после выхода возвращает в тот же тенант")
def test_user_relogins_via_form_lands_in_same_tenant(
    owner_page: Page, owner_user, pages: PageFactory,
) -> None:
    """F-LO-2: после logout повторный вход через форму возвращает в тот же tenant."""
    with step("подготовка: logout"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()
        tree.logout()
        tree.expect_guest_state()

    with step("действие: повторный вход через /login"):
        login = pages.navigate_to(LoginPage)
        login.expect_visible_form()
        login.login(owner_user.email, owner_user.password)

    with step("проверка: redirect на / с тем же tenant и demo-self"):
        owner_page.wait_for_url("**/")
        tree = pages.create(TreePage)
        tree.expect_authed_state(TestData.DEFAULT_FULL_NAME)
        expect(tree.orbit_center, ErrMsg.orbit_card_not_visible).to_be_visible()
        expect(tree.orbit_center, ErrMsg.wrong_text_content).to_contain_text(
            TestData.DEFAULT_FULL_NAME,
        )
