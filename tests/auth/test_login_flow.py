"""Login flow (этап 3 funnel).

Covers: F-LG-1..4, X-LG-1..4, S-LG-1..2.
"""

from __future__ import annotations

import re

import allure
import httpx
from playwright.sync_api import Page, expect

from tests.messages import Links, t
from tests.pages.login_page import LoginPage
from tests.response import expect_response
from tests.step import step
from tests.timeouts import TIMEOUTS


@allure.title("Форма логина содержит поля email, пароль и кнопку входа")
def test_login_form_renders(page: Page):
    """F-LG-1, X-LG-1..4: /login renders email + password + submit."""
    login = LoginPage(page).goto()
    login.expect_visible_form()


@allure.title("Вход с правильным паролем выдаёт сессию и доступ к /me")
def test_login_with_correct_credentials_succeeds(
    page: Page, base_url: str, owner_user
):
    """F-LG-1, F-LG-4: correct credentials → session cookie + /me returns tenant."""
    with step("действие: вход с правильными credentials"):
        login = LoginPage(page).goto()

        with page.expect_response("**/api/account/login") as resp_info:
            login.login(owner_user.email, owner_user.password)
        assert resp_info.value.ok, f"login response not ok: {resp_info.value.status}"

    with step("проверка: session cookie установлена"):
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        session_cookie = cookies.get("platform_session") or cookies.get("session_id")
        assert session_cookie, f"no platform_session/session_id cookie set after login: {cookies}"

    with step("проверка: /me возвращает правильный tenant"):
        me = httpx.get(f"{base_url}/api/account/me", cookies=cookies, timeout=TIMEOUTS.api_request)
        expect_response(me, label="/me after login").status_ok()
        assert me.json()["tenant"]["slug"] == owner_user.slug, \
            f"/me tenant slug: expected {owner_user.slug!r}, got {me.json()['tenant']['slug']!r}"


@allure.title("Неверный пароль показывает ошибку на странице логина")
def test_login_with_wrong_password_shows_error(page: Page, owner_user):
    """S-LG-1: wrong credentials → visible inline error, no redirect away from /login."""
    with step("действие: вход с неверным паролем"):
        login = LoginPage(page).goto()
        login.login(owner_user.email, "wrong_password_xyz")

    with step("проверка: ошибка видна и URL остался /login"):
        expect(login.error_msg).to_be_visible()
        expect(page).to_have_url(re.compile(r"/login"))


@allure.title("Ошибки для неизвестного email и неверного пароля одинаковы")
def test_login_unknown_email_returns_same_error_as_wrong_password(
    page: Page, owner_user
):
    """S-LG-1, S-SU-2: unknown email vs wrong password — identical error text.

    No reverse-engineerable signal that an account does/does-not exist.
    """
    # `to_be_visible` would pass while the element is still rendering its
    # text; under `-n auto` parallel load that race yields a spurious empty
    # `text_content()`. Wait for non-empty text so the comparison is
    # between two settled strings.
    _NON_EMPTY = re.compile(r"\S")

    with step("действие: вход с неверным паролем для известного email"):
        login = LoginPage(page).goto()
        login.login(owner_user.email, "wrong_pw_2026")
        expect(login.error_msg).to_have_text(_NON_EMPTY, timeout=TIMEOUTS.pw_action_ms)
        msg_known = login.error_msg.text_content()

    with step("действие: вход с неизвестным email"):
        page.goto("/login")
        login_unknown = LoginPage(page)
        login_unknown.login("does-not-exist@e2e.example.com", "any_password_2026")
        expect(login_unknown.error_msg).to_have_text(_NON_EMPTY, timeout=TIMEOUTS.pw_action_ms)
        msg_unknown = login_unknown.error_msg.text_content()

    with step("проверка: тексты ошибок идентичны (anti-enumeration)"):
        assert msg_known == msg_unknown, (
            f"login error texts differ — possible enumeration leak.\n"
            f"  known:   {msg_known!r}\n  unknown: {msg_unknown!r}"
        )


@allure.title("Страница логина содержит ссылки на регистрацию и сброс пароля")
def test_login_links_to_signup_and_forgot(page: Page):
    """X-LG-1, X-LG-2: signup and forgot-password links visible on /login."""
    with step("действие: переход на /login"):
        page.goto("/login")

    with step("проверка: ссылки на регистрацию и сброс пароля видны"):
        expect(page.get_by_role("link", name=t(Links.SIGNUP))).to_be_visible()
        expect(page.get_by_role("link", name=t(Links.FORGOT_PASSWORD))).to_be_visible()
