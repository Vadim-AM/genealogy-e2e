"""Logout flow — F-LO-1..2 user-flow E2E.

Тесты через UI, не через httpx: проверяем что юзер кликом по «Выйти» в
header'е сбрасывает session, и при повторном /login возвращается в свой
же tenant. UI-flow ловит регрессии, которые API не видит:
- logout-link исчез или сменил label;
- doLogout race с auth-indicator update — guest UI не отрисовался;
- map/sources/timeline tabs остались видны после logout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
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
    """F-LO-1: клик по «Выйти» сбрасывает session и переключает UI в guest.

    Контракт:
    1. Header `#authIndicator` показывает имя authenticated юзера ДО клика.
    2. После клика появляется `Войти` / `Регистрация` (guest indicator).
    3. Tabs map/sources/timeline скрываются (updateGuestUI).
    4. POST /api/account/logout улетел (cookie на server-side dead).
    """
    with step("подготовка: загрузка страницы и проверка authed-состояния"):
        _ = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)

        auth_indicator(owner_page)
        expect(auth_name(owner_page), ErrMsg.auth_name_wrong).to_have_text(TestData.DEFAULT_FULL_NAME)
        expect(logout_link(owner_page), ErrMsg.logout_link_not_visible).to_be_visible()

        # Authed: map tab visible (CSS display reset из updateGuestUI).
        map_tab_before = owner_page.locator('[data-tab="map"]')

    with step("действие: клик по кнопке 'Выйти'"), owner_page.expect_response(
        lambda r: routes.LOGOUT in r.url and r.request.method == "POST"
    ):
        logout_link(owner_page).click()

    with step("проверка: UI переключился в гостевой режим"):
        # Guest indicator появляется после updateAuthIndicator.
        expect(login_link(owner_page), ErrMsg.link_not_visible).to_be_visible()
        expect(auth_name(owner_page), ErrMsg.wrong_count).to_have_count(0)

        # updateGuestUI hides auth-only tabs — visibility=false (style.display='none').
        expect(map_tab_before, ErrMsg.tab_should_be_hidden).to_be_hidden()
        expect(owner_page.locator('[data-tab="sources"]'), ErrMsg.tab_should_be_hidden).to_be_hidden()
        expect(owner_page.locator('[data-tab="timeline"]'), ErrMsg.tab_should_be_hidden).to_be_hidden()


@allure.title("Повторный вход после выхода возвращает в тот же тенант")
def test_user_relogins_via_form_lands_in_same_tenant(
    owner_page: Page, owner_user, pages: PageFactory,
) -> None:
    """F-LO-2: после logout юзер логинится снова через `/login` форму
    и попадает в **тот же tenant** (slug сохраняется).

    UI-проверка: на главной после login видим tenant-display-name owner'а
    (он же `full_name` — см. owner_user fixture в conftest).
    """
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
        assert resp_ctx.value.ok, (
            f"login POST failed: {resp_ctx.value.status} {resp_ctx.value.text()[:200]}"
        )

    with step("проверка: redirect на / с тем же tenant и demo-self"):
        owner_page.wait_for_url("**/")
        expect(
            auth_indicator(owner_page).locator('[data-testid="auth-user-name"]'),
            ErrMsg.auth_name_wrong,
        ).to_have_text(
            TestData.DEFAULT_FULL_NAME
        )

        orbit_center = owner_page.locator('[data-testid="orbit-center-card"]')
        expect(orbit_center, ErrMsg.orbit_card_not_visible).to_be_visible()
        expect(orbit_center, ErrMsg.wrong_text_content).to_contain_text(TestData.DEFAULT_FULL_NAME)
