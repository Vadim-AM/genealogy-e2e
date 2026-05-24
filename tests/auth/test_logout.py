"""Logout flow — F-LO-1..2 user-flow E2E."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.step import step
from helpers.auth.auth_ui import auth_indicator, auth_name, login_link, logout_link
from pages.base import wait_for_authed_shell
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
    with step("подготовка: загрузка страницы и проверка authed-состояния"):
        _ = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)

        auth_indicator(owner_page)
        expect(auth_name(owner_page), ErrMsg.auth_name_wrong).to_have_text(TestData.DEFAULT_FULL_NAME)
        expect(logout_link(owner_page), ErrMsg.logout_link_not_visible).to_be_visible()

        map_tab_before = owner_page.locator('[data-tab="map"]')

    with step("действие: клик по кнопке 'Выйти'"), owner_page.expect_response(
        lambda r: routes.LOGOUT in r.url and r.request.method == "POST"
    ):
        logout_link(owner_page).click()

    with step("проверка: UI переключился в гостевой режим"):
        expect(login_link(owner_page), ErrMsg.link_not_visible).to_be_visible()
        expect(auth_name(owner_page), ErrMsg.wrong_count).to_have_count(0)

        expect(map_tab_before, ErrMsg.tab_should_be_hidden).to_be_hidden()
        expect(owner_page.locator('[data-tab="sources"]'), ErrMsg.tab_should_be_hidden).to_be_hidden()
        expect(owner_page.locator('[data-tab="timeline"]'), ErrMsg.tab_should_be_hidden).to_be_hidden()


@allure.title("Повторный вход после выхода возвращает в тот же тенант")
def test_user_relogins_via_form_lands_in_same_tenant(
    owner_page: Page, owner_user, pages: PageFactory,
) -> None:
    """F-LO-2: после logout повторный вход через форму возвращает в тот же tenant."""
    with step("подготовка: logout для перехода в guest state"):
        _ = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)
        expect(logout_link(owner_page), ErrMsg.logout_link_not_visible).to_be_visible()
        with owner_page.expect_response(
            lambda r: routes.LOGOUT in r.url and r.request.method == "POST"
        ):
            logout_link(owner_page).click()
        expect(login_link(owner_page), ErrMsg.link_not_visible).to_be_visible()

    with step("действие: повторный вход через форму /login"):
        login = pages.navigate_to(LoginPage)
        login.expect_visible_form()
        with owner_page.expect_response(
            lambda r: routes.LOGIN in r.url and r.request.method == "POST"
        ) as resp_ctx:
            login.login(owner_user.email, owner_user.password)
        should.playwright_ok(resp_ctx.value, ErrMsg.login_response_not_ok)

    with step("проверка: redirect на / с тем же tenant и demo-self"):
        owner_page.wait_for_url("**/")
        expect(
            # no semantic: data-testid element, no role
            auth_indicator(owner_page).locator('[data-testid="auth-user-name"]'),
            ErrMsg.auth_name_wrong,
        ).to_have_text(
            TestData.DEFAULT_FULL_NAME
        )

        # no semantic: data-testid element, no role
        orbit_center = owner_page.locator('[data-testid="orbit-center-card"]')
        expect(orbit_center, ErrMsg.orbit_card_not_visible).to_be_visible()
        expect(orbit_center, ErrMsg.wrong_text_content).to_contain_text(TestData.DEFAULT_FULL_NAME)
