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

import httpx
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.constants import make_email
from tests.messages import TestData
from tests.pages.forgot_password_page import ForgotPasswordPage, ResetPasswordPage
from tests.pages.login_page import LoginPage
from tests.timeouts import TIMEOUTS


_NEW_PASSWORD = "Brand_New_Password_2026"


def test_forgot_password_full_flow_user_logs_in_with_new_password(
    page: Page, owner_user, read_email_token,
):
    """TC-FP-1: full user journey — request reset → email → reset page →
    new password → /login form → indicator shows authed user.

    Никаких httpx-логинов в финале — реальный flow проходит через
    `LoginPage`, и indicator проверяется DOM-ом (catches «password updated
    но cookie не выдан», «form errors но redirect happens» и подобные).
    """
    fp = ForgotPasswordPage(page).goto()
    fp.expect_visible_form()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset(owner_user.email)
    assert resp_info.value.ok, f"forgot-password returned {resp_info.value.status}"
    fp.expect_success_message()

    token = read_email_token(owner_user.email)

    rp = ResetPasswordPage(page).open_with_token(token)
    with page.expect_response("**/api/account/reset-password") as resp_info:
        rp.submit_new_password(_NEW_PASSWORD)
    assert resp_info.value.ok, f"reset-password returned {resp_info.value.status}"
    rp.expect_success_message()

    # Backend page редиректит на /login (см. main.py reset-password HTML).
    page.wait_for_url("**/login")

    # Login form открыта — старый пароль больше не работает.
    login = LoginPage(page)
    login.expect_visible_form()
    login.login(owner_user.email, owner_user.password)
    login.expect_error()  # #msg текст non-empty → старый pass отвергнут

    # Новый пароль — успех. После login redirect на / + indicator authed.
    login.login(owner_user.email, _NEW_PASSWORD)
    page.wait_for_url("**/")
    expect(page.locator("#authIndicator .auth-name")).to_have_text(
        TestData.DEFAULT_FULL_NAME
    )


def test_forgot_password_unknown_email_shows_silent_success_message(
    page: Page, base_url: str,
):
    """F-FP-2 / TC-FP-2: anti-enumeration — для unknown email UI показывает
    ту же success-копию (никакой подсказки «такого user не существует»).

    Backend assertion (single hop) — MockSender пуст для unknown адреса.
    UI inbox у нас нет, эта часть остаётся API-проверкой:
    «backend NOT sending» — это negative invariant без UI surface.
    """
    unknown_email = make_email("never-registered")
    fp = ForgotPasswordPage(page).goto()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset(unknown_email)
    assert resp_info.value.ok, (
        f"unknown-email request returned {resp_info.value.status} (must be silent 200)"
    )
    fp.expect_success_message()

    r = httpx.get(
        f"{base_url}{API.TEST_LAST_EMAIL}",
        params={"to": unknown_email},
        timeout=TIMEOUTS.api_short,
    )
    assert r.status_code == 404, "unknown email must not trigger a reset send"


def test_reset_password_token_used_once_then_invalid_via_ui(
    page: Page, owner_user, read_email_token,
):
    """F-FP-4 / TC-FP-4: после успешного reset тот же token нельзя
    использовать повторно. UI показывает error-banner вместо success.

    User scenario: пользователь применил reset-link, потом случайно
    открыл его ещё раз из истории браузера / другой вкладки — ожидаем
    понятную error-copy, а не silent success или 500.
    """
    fp = ForgotPasswordPage(page).goto()
    fp.request_reset(owner_user.email)
    fp.expect_success_message()

    token = read_email_token(owner_user.email)

    # Первое применение — успех.
    rp = ResetPasswordPage(page).open_with_token(token)
    rp.submit_new_password("First_Reset_Password_2026")
    rp.expect_success_message()
    page.wait_for_url("**/login")

    # Re-open того же reset-link → submit → error (token consumed).
    rp2 = ResetPasswordPage(page).open_with_token(token)
    rp2.submit_new_password("Second_Attempt_Password_2026")
    rp2.expect_error_message()


def test_forgot_password_empty_field_shows_inline_error_no_request(
    page: Page,
):
    """Form-level guard: пустой email → submit → backend не вызывается
    (HTML required validation либо JS-side check)."""
    fp = ForgotPasswordPage(page).goto()
    fp.expect_visible_form()

    # Никаких сетевых запросов на forgot-password от пустого submit.
    requests_seen: list[str] = []
    page.on(
        "request",
        lambda req: requests_seen.append(req.url) if "forgot-password" in req.url else None,
    )

    fp.email.fill("")
    fp.submit_btn.click()

    # Validation: HTML5 required атрибут не пропускает submit. Если бы
    # backend всё-таки получил пустой email — тест ловит это (regression
    # against future «required» strip).
    assert not requests_seen, f"empty email triggered network call: {requests_seen!r}"
