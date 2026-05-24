"""Forgot-password / reset-password — TC-FP-1..6 user-flow E2E.

Полный путь юзера через UI:
1. /account/forgot-password → fill email → submit.
2. MockSender capture reset-link (через test endpoint — single API hop —
   симуляция реального email-чтения; нет UI surface для inbox).
3. /account/reset-password?token=… → fill new password (×2) → submit.
4. Redirect на /login → log in новым паролем → indicator authed.

UI-flow ловит: success/error banner state на reset-page, redirect timing,
empty-password validation, login form readiness, success copy.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from tests._core import api_paths as routes
from tests._core.constants import make_email
from tests._core.err_msg import ErrMsg
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests.helpers.auth.auth_ui import auth_name
from tests.pages.forgot_password_page import ForgotPasswordPage, ResetPasswordPage
from tests.pages.login_page import LoginPage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory

_NEW_PASSWORD = "Brand_New_Password_2026"


@allure.title("Сброс пароля: полный путь от запроса до входа с новым паролем")
def test_forgot_password_full_flow_user_logs_in_with_new_password(
    page: Page, owner_user, read_email_token, anon_pages: PageFactory,
):
    """TC-FP-1: full user journey — request reset → email → reset page →
    new password → /login form → indicator shows authed user.

    Никаких httpx-логинов в финале — реальный flow проходит через
    `LoginPage`, и indicator проверяется DOM-ом (catches «password updated
    но cookie не выдан», «form errors но redirect happens» и подобные).
    """
    with step("действие: запрос сброса пароля через UI"):
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        fp.expect_visible_form()
        with page.expect_response("**/api/account/forgot-password") as resp_info:
            fp.request_reset(owner_user.email)
        assert resp_info.value.ok, f"forgot-password returned {resp_info.value.status}"
        fp.expect_success_message()

    with step("действие: получение токена и сброс пароля"):
        token = read_email_token(owner_user.email)

        rp = ResetPasswordPage(page).open_with_token(token)
        with page.expect_response("**/api/account/reset-password") as resp_info:
            rp.submit_new_password(_NEW_PASSWORD)
        assert resp_info.value.ok, f"reset-password returned {resp_info.value.status}"
        rp.expect_success_message()

    with step("проверка: старый пароль не работает"):
        # Backend page редиректит на /login (см. main.py reset-password HTML).
        page.wait_for_url("**/login")

        # Login form открыта — старый пароль больше не работает.
        login = LoginPage(page)
        login.expect_visible_form()
        login.login(owner_user.email, owner_user.password)
        login.expect_error()  # #msg текст non-empty → старый pass отвергнут

    with step("проверка: вход с новым паролем успешен"):
        # Новый пароль — успех. После login redirect на / + indicator authed.
        login.login(owner_user.email, _NEW_PASSWORD)
        page.wait_for_url("**/")
        expect(auth_name(page), ErrMsg.auth_name_wrong).to_have_text(
            TestData.DEFAULT_FULL_NAME
        )


@allure.title("Запрос сброса для неизвестного email показывает тот же успех")
def test_forgot_password_unknown_email_shows_silent_success_message(
    page: Page, base_url: str, anon_pages: PageFactory,
):
    """F-FP-2 / TC-FP-2: anti-enumeration — для unknown email UI показывает
    ту же success-копию (никакой подсказки «такого user не существует»).

    Backend assertion (single hop) — MockSender пуст для unknown адреса.
    UI inbox у нас нет, эта часть остаётся API-проверкой:
    «backend NOT sending» — это negative invariant без UI surface.
    """
    with step("действие: запрос сброса для неизвестного email"):
        unknown_email = make_email("never-registered")
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        with page.expect_response("**/api/account/forgot-password") as resp_info:
            fp.request_reset(unknown_email)
        assert resp_info.value.ok, (
            f"unknown-email request returned {resp_info.value.status} (must be silent 200)"
        )
        fp.expect_success_message()

    with step("проверка: письмо не отправлено для неизвестного email"):
        r = httpx.get(
            f"{base_url}{routes.TEST_LAST_EMAIL}",
            params={"to": unknown_email},
            timeout=TIMEOUTS.api_short,
        )
        expect_response(r, label="unknown email: no reset sent").status(HTTPStatus.NOT_FOUND)


@allure.title("Повторное открытие ссылки сброса пароля показывает ошибку")
def test_reset_password_token_used_once_then_invalid_via_ui(
    page: Page, owner_user, read_email_token, anon_pages: PageFactory,
):
    """F-FP-4 / TC-FP-4: после успешного reset тот же token нельзя
    использовать повторно. UI показывает error-banner вместо success.

    User scenario: пользователь применил reset-link, потом случайно
    открыл его ещё раз из истории браузера / другой вкладки — ожидаем
    понятную error-copy, а не silent success или 500.
    """
    with step("подготовка: запрос сброса и получение токена"):
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        fp.request_reset(owner_user.email)
        fp.expect_success_message()
        token = read_email_token(owner_user.email)

    with step("действие: первое использование токена — успех"):
        rp = ResetPasswordPage(page).open_with_token(token)
        rp.submit_new_password("First_Reset_Password_2026")
        rp.expect_success_message()
        page.wait_for_url("**/login")

    with step("проверка: повторное использование токена — ошибка"):
        rp2 = ResetPasswordPage(page).open_with_token(token)
        rp2.submit_new_password("Second_Attempt_Password_2026")
        rp2.expect_error_message()


@allure.title("Пустое поле email не отправляет запрос на сброс пароля")
def test_forgot_password_empty_field_shows_inline_error_no_request(
    page: Page, anon_pages: PageFactory,
):
    """Form-level guard: пустой email → submit → backend не вызывается
    (HTML required validation либо JS-side check)."""
    with step("подготовка: открытие формы и установка перехватчика"):
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        fp.expect_visible_form()

        # Никаких сетевых запросов на forgot-password от пустого submit.
        requests_seen: list[str] = []
        page.on(
            "request",
            lambda req: requests_seen.append(req.url) if "forgot-password" in req.url else None,
        )

    with step("действие: отправка пустого поля email"):
        fp.email.fill("")
        fp.submit_btn.click()

    with step("проверка: сетевой запрос не отправлен"):
        # Validation: HTML5 required атрибут не пропускает submit. Если бы
        # backend всё-таки получил пустой email — тест ловит это (regression
        # against future «required» strip).
        assert not requests_seen, f"empty email triggered network call: {requests_seen!r}"
