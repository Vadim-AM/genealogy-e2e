"""TC-FORM-1: public forms must POST credentials, never GET."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from config.constants import TestConfig, unique_email
from framework.step import step
from pages.forgot_password_page import ResetPasswordPage
from pages.login_page import LoginPage
from pages.signup_page import SignupPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Формы: регистрация отправляется методом POST, не GET")
def test_signup_form_submits_via_post(page: Page, anon_pages: PageFactory) -> None:
    """Submit signup form отправляет запрос методом POST."""
    with step("подготовка: заполнить форму регистрации"):
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(email=unique_email("formpost"), password=TestConfig.DEFAULT_PASSWORD)

    with (
        step("действие: отправить форму и перехватить запрос"),
        page.expect_request(lambda req: routes.SIGNUP in req.url) as req_info,
    ):
        signup.submit_btn_by_id.click()

    with step("проверка: метод запроса — POST"):
        should.be_equal(req_info.value.method, "POST", ErrMsg.form_method_not_post)
        expect(signup.form, ErrMsg.wrong_attribute).to_have_attribute("method", "post")


@allure.title("Формы: вход отправляется методом POST, не GET")
def test_login_form_submits_via_post(page: Page, anon_pages: PageFactory) -> None:
    """Submit login form отправляет запрос методом POST."""
    with step("подготовка: заполнить форму входа"):
        login = anon_pages.navigate_to(LoginPage)
        login.email.fill(unique_email("formpost-li"))
        login.password.fill("any-password-here")

    with (
        step("действие: отправить форму и перехватить запрос"),
        page.expect_request(lambda req: routes.LOGIN in req.url) as req_info,
    ):
        login.submit_btn.click()

    with step("проверка: метод запроса — POST"):
        should.be_equal(req_info.value.method, "POST", ErrMsg.form_method_not_post)
        expect(login.form, ErrMsg.wrong_attribute).to_have_attribute("method", "post")


@allure.title("Формы: сброс пароля отправляется методом POST, не GET")
def test_reset_password_form_method_is_post(page: Page) -> None:
    """Reset-password form имеет атрибут method=post."""
    with step("действие: открываем страницу сброса пароля"):
        rp = ResetPasswordPage(page)
        rp.open_with_token("fake-for-render")

    with step("проверка: атрибут формы method=post"):
        expect(rp.form, ErrMsg.wrong_attribute).to_have_attribute("method", "post")
