"""TC-FORM-1: public forms must POST credentials, never GET."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from config.constants import TestConfig, unique_email
from framework.step import step
from pages.login_page import LoginPage
from pages.signup_page import SignupPage
from src.texts import Buttons, ErrMsg, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Формы: регистрация отправляется методом POST, не GET")
def test_signup_form_submits_via_post(page: Page, anon_pages: PageFactory) -> None:
    """Submit signup form отправляет запрос методом POST."""
    with step("подготовка: заполнить форму регистрации"):
        _ = anon_pages.navigate_to(SignupPage)
        page.locator("#email").fill(unique_email("formpost"))  # no semantic: form input without label
        page.locator("#password").fill(TestConfig.DEFAULT_PASSWORD)  # no semantic: form input without label
        # Wave-9: privacy/cross-border объединены с terms_accepted (см. backend
        # router.py:417). В форме остался только `#agreeTerms`.
        page.locator("#agreeTerms").check()  # no semantic: form element by ID

    with step("действие: отправить форму и перехватить запрос"), page.expect_request(
        lambda req: routes.SIGNUP in req.url
    ) as req_info:
        page.locator("#signupBtn").click()  # no semantic: submit button without accessible name

    with step("проверка: метод запроса — POST"):
        should.be_equal(req_info.value.method, "POST", ErrMsg.form_method_not_post)
        signup_form = page.locator("#signupForm")  # no semantic: form element by ID
        expect(signup_form, ErrMsg.wrong_attribute).to_have_attribute("method", "post")


@allure.title("Формы: вход отправляется методом POST, не GET")
def test_login_form_submits_via_post(page: Page, anon_pages: PageFactory) -> None:
    """Submit login form отправляет запрос методом POST."""
    with step("подготовка: заполнить форму входа"):
        _ = anon_pages.navigate_to(LoginPage)
        page.locator("#email").fill(unique_email("formpost-li"))  # no semantic: form input without label
        page.locator("#password").fill("any-password-here")  # no semantic: form input without label

    with step("действие: отправить форму и перехватить запрос"), page.expect_request(
        lambda req: routes.LOGIN in req.url
    ) as req_info:
        page.get_by_role("button", name=t(Buttons.LOGIN), exact=False).click()

    with step("проверка: метод запроса — POST"):
        should.be_equal(req_info.value.method, "POST", ErrMsg.form_method_not_post)
        login_form = page.locator("#loginForm")  # no semantic: form element by ID
        expect(login_form, ErrMsg.wrong_attribute).to_have_attribute("method", "post")


@allure.title("Формы: сброс пароля отправляется методом POST, не GET")
def test_reset_password_form_method_is_post(page: Page) -> None:
    """Reset-password form имеет атрибут method=post."""
    with step("действие: открываем страницу сброса пароля"):
        page.goto("/account/reset-password?token=fake-for-render")
        page.wait_for_load_state("domcontentloaded")

    with step("проверка: атрибут формы method=post"):
        # no semantic: form element by ID
        expect(page.locator("#rpForm"), ErrMsg.wrong_attribute).to_have_attribute("method", "post")
