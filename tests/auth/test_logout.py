"""Logout flow — F-LO-1..2 user-flow E2E.

Тесты через UI, не через httpx: проверяем что юзер кликом по «Выйти» в
header'е сбрасывает session, и при повторном /login возвращается в свой
же tenant. UI-flow ловит регрессии, которые API не видит:
- logout-link исчез или сменил label;
- doLogout race с auth-indicator update — guest UI не отрисовался;
- map/sources/timeline tabs остались видны после logout.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.helpers.auth.auth_ui import auth_indicator, auth_name, logout_link, login_link
from tests.messages import TestData
from tests.pages.base import wait_for_authed_shell
from tests.pages.login_page import LoginPage


def test_owner_clicks_logout_link_and_indicator_switches_to_guest(
    owner_page: Page, owner_user,
):
    """F-LO-1: клик по «Выйти» сбрасывает session и переключает UI в guest.

    Контракт:
    1. Header `#authIndicator` показывает имя authenticated юзера ДО клика.
    2. После клика появляется `Войти` / `Регистрация` (guest indicator).
    3. Tabs map/sources/timeline скрываются (updateGuestUI).
    4. POST /api/account/logout улетел (cookie на server-side dead).
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("domcontentloaded")
    # Gate logout-link interaction on the authed SPA being fully wired:
    # the link can be visible (indicator HTML injected) before the
    # delegated data-action handler is bound / AUTH settled → on slow CI
    # the click fired no POST and `expect_response` timed out 30s
    # (test_user_relogins, 2026-05-19). wait_for_authed_shell settles it.
    wait_for_authed_shell(owner_page)

    indicator = auth_indicator(owner_page)
    expect(auth_name(owner_page)).to_have_text(TestData.DEFAULT_FULL_NAME)
    expect(logout_link(owner_page)).to_be_visible()

    # Authed: map tab visible (CSS display reset из updateGuestUI).
    map_tab_before = owner_page.locator('[data-tab="map"]')

    # Click logout — fire-and-forget POST + reset AUTH локально.
    with owner_page.expect_response(
        lambda r: "/api/account/logout" in r.url and r.request.method == "POST"
    ):
        logout_link(owner_page).click()

    # Guest indicator появляется после updateAuthIndicator.
    expect(login_link(owner_page)).to_be_visible()
    expect(auth_name(owner_page)).to_have_count(0)

    # updateGuestUI hides auth-only tabs — visibility=false (style.display='none').
    expect(map_tab_before).to_be_hidden()
    expect(owner_page.locator('[data-tab="sources"]')).to_be_hidden()
    expect(owner_page.locator('[data-tab="timeline"]')).to_be_hidden()


def test_user_relogins_via_form_lands_in_same_tenant(
    owner_page: Page, owner_user,
):
    """F-LO-2: после logout юзер логинится снова через `/login` форму
    и попадает в **тот же tenant** (slug сохраняется).

    UI-проверка: на главной после login видим tenant-display-name owner'а
    (он же `full_name` — см. owner_user fixture в conftest).
    """
    # Сначала logout — чтобы стартовать с guest state.
    owner_page.goto("/")
    owner_page.wait_for_load_state("domcontentloaded")
    # Gate logout-link interaction on the authed SPA being fully wired:
    # the link can be visible (indicator HTML injected) before the
    # delegated data-action handler is bound / AUTH settled → on slow CI
    # the click fired no POST and `expect_response` timed out 30s
    # (test_user_relogins, 2026-05-19). wait_for_authed_shell settles it.
    wait_for_authed_shell(owner_page)
    expect(logout_link(owner_page)).to_be_visible()
    with owner_page.expect_response(
        lambda r: "/api/account/logout" in r.url and r.request.method == "POST"
    ):
        logout_link(owner_page).click()
    expect(login_link(owner_page)).to_be_visible()

    # Re-login через /login форму.
    login = LoginPage(owner_page).goto()
    login.expect_visible_form()
    with owner_page.expect_response(
        lambda r: "/api/account/login" in r.url and r.request.method == "POST"
    ) as resp_ctx:
        login.login(owner_user.email, owner_user.password)
    assert resp_ctx.value.ok, (
        f"login POST failed: {resp_ctx.value.status} {resp_ctx.value.text()[:200]}"
    )

    # После login UI редиректит к / — ждём пока indicator снова authed.
    owner_page.wait_for_url("**/")
    expect(auth_indicator(owner_page).locator('[data-testid="auth-user-name"]')).to_have_text(
        TestData.DEFAULT_FULL_NAME
    )

    # Tenant identity видна через demo-self person в дереве — signup ставит
    # `demo-self.name = full_name`. Если бы redirect занёс в чужой tenant
    # (или fresh tenant без seed), demo-self бы не было либо name был бы
    # другим. orbit-card.first читаем — это центральный subject.
    orbit_center = owner_page.locator('[data-testid="orbit-center-card"]')
    expect(orbit_center).to_be_visible()
    expect(orbit_center).to_contain_text(TestData.DEFAULT_FULL_NAME)
