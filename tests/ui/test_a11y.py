"""TC-A11Y-1, TC-A11Y-2: accessibility regressions on signup form."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from config.constants import make_email
from framework.step import step
from pages.signup_page import SignupPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("A11y: поле пароля получает aria-invalid при ошибке сервера")
def test_signup_short_password_sets_aria_invalid(page: Page, anon_pages: PageFactory) -> None:
    """A-SU-3: server returns 422 на short password → JS handler ставит."""
    with step("подготовка: открыть signup и снять minlength"):
        signup = anon_pages.navigate_to(SignupPage)
        # Снимаем HTML5 ограничение minlength="8" на #password — иначе native
        # validity блокирует submit ДО fetch, JS error-handler не запускается,
        # тест проверяет уровень `aria-invalid` который ставится только из
        # response-handler. Server-side валидация (zxcvbn-python score>=2) —
        # источник истины, который мы и тестируем.
        signup.remove_password_minlength()

    with step("действие: заполнить форму коротким паролем и отправить"):
        signup.fill_credentials(email=make_email("a11y-server"), password="short")  # < 8 chars — server rejects
        # Wave-9: privacy/cross-border объединены с terms_accepted.
        signup.agree_terms.check()

        # Ждём ответ сервера, затем проверяем aria-состояние.
        with page.expect_response("**/api/account/signup") as resp_info:
            signup.submit()
        should.greater_or_equal(resp_info.value.status, HTTPStatus.BAD_REQUEST, ErrMsg.status_mismatch)

    with step("проверка: поле пароля получило aria-invalid"):
        expect(signup.password, ErrMsg.wrong_attribute).to_have_attribute("aria-invalid", "true")


@allure.title("A11y: honeypot-поле скрыто от скринридера (aria-hidden)")
def test_signup_honeypot_is_aria_hidden(anon_pages: PageFactory) -> None:
    """A-SU-4: honeypot input has `aria-hidden="true"` (or its wrapper)."""
    with step("действие: открыть signup"):
        signup = anon_pages.navigate_to(SignupPage)

    with step("проверка: honeypot имеет aria-hidden"):
        expect(signup.honeypot, ErrMsg.wrong_attribute).to_have_attribute("aria-hidden", "true")
