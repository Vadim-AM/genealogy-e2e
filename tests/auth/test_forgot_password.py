"""Forgot-password / reset-password — TC-FP-1..6 user-flow E2E."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from pages.forgot_password_page import ForgotPasswordPage, ResetPasswordPage
from pages.login_page import LoginPage
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser

_NEW_PASSWORD = "Brand_New_Password_2026"


@allure.title("Сброс пароля: полный путь от запроса до входа с новым паролем")
def test_forgot_password_full_flow_user_logs_in_with_new_password(
    page: Page, owner_user: AuthUser, read_email_token: Callable[[str], str], anon_pages: PageFactory
) -> None:
    """TC-FP-1: полный путь — запрос сброса → email → новый пароль → вход."""
    with step("действие: запрос сброса пароля через UI"):
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        fp.expect_visible_form()
        with page.expect_response("**/api/account/forgot-password") as resp_info:
            fp.request_reset(owner_user.email)
        should.playwright_ok(resp_info.value, ErrMsg.forgot_response_not_ok)
        fp.expect_success_message()

    with step("действие: получение токена и сброс пароля"):
        token = read_email_token(owner_user.email)

        rp = ResetPasswordPage(page).open_with_token(token)
        with page.expect_response("**/api/account/reset-password") as resp_info:
            rp.submit_new_password(_NEW_PASSWORD)
        should.playwright_ok(resp_info.value, ErrMsg.reset_response_not_ok)
        rp.expect_success_message()

    with step("проверка: старый пароль не работает"):
        page.wait_for_url("**/login")

        login = anon_pages.create(LoginPage)
        login.expect_visible_form()
        login.login(owner_user.email, owner_user.password)
        login.expect_error()

    with step("проверка: вход с новым паролем успешен"):
        login.login(owner_user.email, _NEW_PASSWORD)
        page.wait_for_url("**/")
        tree = anon_pages.create(TreePage)
        expect(tree.auth_user_name, ErrMsg.auth_name_wrong).to_have_text(TestData.DEFAULT_FULL_NAME)


@allure.title("Запрос сброса для неизвестного email показывает тот же успех")
def test_forgot_password_unknown_email_shows_silent_success_message(
    page: Page,
    base_url: str,
    anon_pages: PageFactory,
) -> None:
    """F-FP-2 / TC-FP-2: для unknown email UI показывает ту же success-копию."""
    with step("действие: запрос сброса для неизвестного email"):
        unknown_email = unique_email("never-registered")
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        with page.expect_response("**/api/account/forgot-password") as resp_info:
            fp.request_reset(unknown_email)
        should.playwright_ok(resp_info.value, ErrMsg.forgot_response_not_ok)
        fp.expect_success_message()

    with step("проверка: письмо не отправлено для неизвестного email"):
        r = httpx.get(
            f"{base_url}{routes.TEST_LAST_EMAIL}",
            params={"to": unknown_email},
        )
        expect_response(r, label="unknown email: no reset sent").status(HTTPStatus.NOT_FOUND)


@allure.title("Повторное открытие ссылки сброса пароля показывает ошибку")
def test_reset_password_token_used_once_then_invalid_via_ui(
    page: Page, owner_user: AuthUser, read_email_token: Callable[[str], str], anon_pages: PageFactory
) -> None:
    """F-FP-4 / TC-FP-4: после reset тот же token нельзя использовать повторно."""
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
    page: Page,
    anon_pages: PageFactory,
    forgot_password_request_spy: list[str],
) -> None:
    """Пустой email → submit → backend не вызывается (HTML required)."""
    with step("подготовка: открытие формы"):
        fp = anon_pages.navigate_to(ForgotPasswordPage)
        fp.expect_visible_form()

    with step("действие: отправка пустого поля email"):
        fp.fill_email("")
        fp.click_submit()

    with step("проверка: сетевой запрос не отправлен"):
        should.be_empty(forgot_password_request_spy, ErrMsg.empty_email_triggered_request)
