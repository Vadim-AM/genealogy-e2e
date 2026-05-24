"""Login flow (этап 3 funnel).

Covers: F-LG-1..4, X-LG-1..4, S-LG-1..2.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from pages.login_page import LoginPage
from src.texts import ErrMsg, Links, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Форма логина содержит поля email, пароль и кнопку входа")
def test_login_form_renders(anon_pages: PageFactory):
    """F-LG-1, X-LG-1..4: /login renders email + password + submit."""
    login = anon_pages.navigate_to(LoginPage)
    login.expect_visible_form()


@allure.title("Вход с правильным паролем выдаёт сессию и доступ к /me")
def test_login_with_correct_credentials_succeeds(
    page: Page, base_url: str, owner_user, anon_pages: PageFactory
):
    """F-LG-1, F-LG-4: correct credentials → session cookie + /me returns tenant."""
    with step("действие: вход с правильными credentials"):
        login = anon_pages.navigate_to(LoginPage)

        with page.expect_response("**/api/account/login") as resp_info:
            login.login(owner_user.email, owner_user.password)
        assert resp_info.value.ok, f"login response not ok: {resp_info.value.status}"

    with step("проверка: session cookie установлена"):
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        session_cookie = cookies.get("platform_session") or cookies.get("session_id")
        assert session_cookie, f"no platform_session/session_id cookie set after login: {cookies}"

    with step("проверка: /me возвращает правильный tenant"):
        me = httpx.get(f"{base_url}{routes.ACCOUNT_ME}", cookies=cookies)
        expect_response(me, label="/me after login").status_ok()
        assert me.json()["tenant"]["slug"] == owner_user.slug, \
            f"/me tenant slug: expected {owner_user.slug!r}, got {me.json()['tenant']['slug']!r}"


@allure.title("Неверный пароль показывает ошибку на странице логина")
def test_login_with_wrong_password_shows_error(page: Page, owner_user, anon_pages: PageFactory):
    """S-LG-1: wrong credentials → visible inline error, no redirect away from /login."""
    with step("действие: вход с неверным паролем"):
        login = anon_pages.navigate_to(LoginPage)
        login.login(owner_user.email, "wrong_password_xyz")

    with step("проверка: ошибка видна и URL остался /login"):
        expect(login.error_msg, ErrMsg.login_error_not_visible).to_be_visible()
        expect(page, ErrMsg.url_wrong).to_have_url(re.compile(r"/login"))


@allure.title("Ошибки для неизвестного email и неверного пароля одинаковы")
def test_login_unknown_email_returns_same_error_as_wrong_password(
    page: Page, owner_user, anon_pages: PageFactory
):
    """S-LG-1, S-SU-2: unknown email vs wrong password — identical error text.

    No reverse-engineerable signal that an account does/does-not exist.
    """
    # `to_be_visible` пройдёт, пока элемент ещё рендерит свой текст;
    # под `-n auto` при параллельной нагрузке эта гонка даёт ложный пустой
    # `text_content()`. Ждём непустой текст, чтобы сравнение было
    # между двумя устоявшимися строками.
    _NON_EMPTY = re.compile(r"\S")

    with step("действие: вход с неверным паролем для известного email"):
        login = anon_pages.navigate_to(LoginPage)
        login.login(owner_user.email, "wrong_pw_2026")
        expect(login.error_msg, ErrMsg.wrong_text_content).to_have_text(_NON_EMPTY, timeout=TIMEOUTS.pw_action_ms)
        msg_known = login.error_msg.text_content()

    with step("действие: вход с неизвестным email"):
        login_unknown = anon_pages.navigate_to(LoginPage)
        login_unknown.login("does-not-exist@e2e.example.com", "any_password_2026")
        expect(
            login_unknown.error_msg, ErrMsg.wrong_text_content,
        ).to_have_text(_NON_EMPTY, timeout=TIMEOUTS.pw_action_ms)
        msg_unknown = login_unknown.error_msg.text_content()

    with step("проверка: тексты ошибок идентичны (anti-enumeration)"):
        assert msg_known == msg_unknown, (
            f"login error texts differ — possible enumeration leak.\n"
            f"  known:   {msg_known!r}\n  unknown: {msg_unknown!r}"
        )


@allure.title("Страница логина содержит ссылки на регистрацию и сброс пароля")
def test_login_links_to_signup_and_forgot(page: Page, anon_pages: PageFactory):
    """X-LG-1, X-LG-2: signup and forgot-password links visible on /login."""
    with step("действие: переход на /login"):
        _ = anon_pages.navigate_to(LoginPage)

    with step("проверка: ссылки на регистрацию и сброс пароля видны"):
        expect(page.get_by_role("link", name=t(Links.SIGNUP)), ErrMsg.link_not_visible).to_be_visible()
        expect(page.get_by_role("link", name=t(Links.FORGOT_PASSWORD)), ErrMsg.link_not_visible).to_be_visible()
