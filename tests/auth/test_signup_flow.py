"""Signup + email verification flow — F-SU-1..7, X-SU-1..11, F-EV-1..8, S-SU-3/4."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from config.constants import TestConfig, make_email
from framework.response import expect_response
from framework.step import step
from pages.signup_page import SignupPage
from pages.verify_page import VerifyPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Форма регистрации содержит обязательные поля и honeypot")
def test_signup_form_has_required_inputs(anon_pages: PageFactory, soft_check) -> None:
    """F-SU-1, X-SU-1..11: обязательные поля + autocomplete + honeypot tabindex."""
    signup = anon_pages.navigate_to(SignupPage)
    signup.expect_visible_form()
    signup.soft_check_form_basics(soft_check)


@allure.title("Успешная регистрация отправляет письмо с токеном верификации")
def test_signup_happy_path_sends_verification_email(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """F-SU-1, F-EV-1: отправка формы → backend отправляет verification email."""
    with step("действие: заполнение и отправка формы регистрации"):
        email = make_email("happy")
        signup = anon_pages.navigate_to(SignupPage)

        with page.expect_response("**/api/account/signup") as resp_info:
            signup.fill_required(
                email=email,
                password=TestConfig.DEFAULT_PASSWORD,
                full_name="Иванов Иван",
            ).submit()
        should.playwright_status(resp_info.value, HTTPStatus.OK, ErrMsg.signup_response_not_ok)

        signup.expect_verification_message()

    with step("проверка: письмо с токеном верификации отправлено"):
        r = httpx.get(f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="last-email").status_ok()
        should.contain(r.json()["text_body"] or "", "token=", ErrMsg.verify_token_missing)


@allure.title("Подтверждение email автоматически авторизует пользователя")
def test_verify_email_auto_logs_in_via_set_cookie(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """TC-FLOW-1.1: POST /api/account/verify-email выдаёт session cookie для auto-login."""
    with step("подготовка: signup и получение токена верификации"):
        email = make_email("autologin")
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=email,
            password=TestConfig.DEFAULT_PASSWORD,
            full_name="Автологин Тестов",
        ).submit()
        signup.expect_verification_message()

        mail = httpx.get(
            f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": email}
        )
        expect_response(mail, label="last-email").status_ok()
        m = re.search(r"token=([\w\-]+)", mail.json()["text_body"])
        should.not_none(m, ErrMsg.verify_token_missing)
        token = m.group(1)

    with step("действие: verify-email и проверка auto_login"):
        verify = httpx.post(
            f"{base_url}{routes.VERIFY_EMAIL}", json={"token": token}
        )
        expect_response(verify, label="verify-email").status_ok()
        body = verify.json()
        should.be_equal(body.get("auto_login"), True, ErrMsg.verify_auto_login_missing)
        should.be_true(body.get("tenant_slug"), ErrMsg.verify_slug_missing)

    with step("проверка: session cookie установлена и /me доступен"):
        cookies = dict(verify.cookies)
        session_cookie = cookies.get("platform_session") or cookies.get("session_id")
        should.be_true(session_cookie, ErrMsg.verify_cookie_missing)

        me = httpx.get(f"{base_url}{routes.ACCOUNT_ME}", cookies=cookies)
        expect_response(me, label="/me after verify").status_ok()
        should.be_equal(me.json()["tenant"]["slug"], body["tenant_slug"], ErrMsg.verify_slug_mismatch)


@allure.title("После верификации email создаётся тенант для пользователя")
def test_signup_then_verify_creates_tenant(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """F-EV-4: после верификации login возвращает tenant_slug."""
    with step("подготовка: signup и получение токена"):
        email = make_email("verify")
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=email,
            password=TestConfig.DEFAULT_PASSWORD,
            full_name="Петр Петров",
        ).submit()
        signup.expect_verification_message()

        mail = httpx.get(
            f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": email}
        )
        expect_response(mail, label="last-email").status_ok()
        m = re.search(r"token=([\w\-]+)", mail.json()["text_body"])
        should.not_none(m, ErrMsg.verify_token_missing)
        token = m.group(1)

    with step("действие: верификация email через UI"):
        anon_pages.create(VerifyPage).open_with_token(token).expect_success()

    with step("проверка: login возвращает tenant_slug"):
        me = httpx.post(
            f"{base_url}{routes.LOGIN}",
            json={"email": email, "password": TestConfig.DEFAULT_PASSWORD},
        )
        expect_response(me, label="login after verify").status_ok()
        should.be_true(me.json()["tenant_slug"], ErrMsg.tenant_slug_missing)


@allure.title("Заполненный honeypot даёт тихий 200 без отправки письма")
def test_honeypot_field_silently_succeeds(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """S-SU-4: заполненный honeypot → тихий 200, письмо не отправлено."""
    with step("действие: заполнение формы с honeypot и отправка"):
        email = make_email("bot")
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_honeypot_via_js(
            email=email,
            password=TestConfig.DEFAULT_PASSWORD,
            honeypot="http://spam.example.com",
        )

        with page.expect_response("**/api/account/signup") as resp_info:
            signup.submit_btn_by_id.click()
        should.playwright_status(resp_info.value, HTTPStatus.OK, ErrMsg.signup_response_not_ok)

    with step("проверка: письмо не отправлено"):
        r = httpx.get(f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="honeypot: no email sent").status(HTTPStatus.NOT_FOUND)


@allure.title("Одноразовый email отклоняется с ошибкой в поле ввода")
def test_disposable_email_rejected_inline(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """S-SU-5: одноразовый email → inline error, письмо не отправлено."""
    with step("действие: попытка регистрации с одноразовым email"):
        disposable_email = "spam@mailinator.com"
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=disposable_email,
            password=TestConfig.DEFAULT_PASSWORD,
        ).submit()

    with step("проверка: inline-ошибка в поле email и письмо не отправлено"):
        expect(signup.email_error, ErrMsg.wrong_text_content).not_to_have_text("")
        expect(signup.email, ErrMsg.wrong_attribute).to_have_attribute("aria-invalid", "true")

        r = httpx.get(f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": disposable_email})
        expect_response(r, label="disposable: no email sent").status(HTTPStatus.NOT_FOUND)


@allure.title("Слишком короткий пароль не проходит валидацию формы")
def test_password_too_short_rejected_inline(page: Page, base_url: str, anon_pages: PageFactory) -> None:
    """S-SU-8: пароль < 8 символов → HTML5 validity блокирует submit."""
    with step("действие: попытка регистрации с коротким паролем"):
        email = make_email("shortpw")
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=email,
            password="123",
        ).submit()

    with step("проверка: HTML5 validation не пропускает и письмо не отправлено"):
        pwd_valid = signup.check_password_validity()
        should.be_false(pwd_valid, ErrMsg.password_validity_expected_false)

        r = httpx.get(f"{base_url}{routes.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="short-pw: no email sent").status(HTTPStatus.NOT_FOUND)
