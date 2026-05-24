"""Signup + email verification flow (этапы 1-2 funnel).

Covers: F-SU-1..7, X-SU-1..11, F-EV-1..8, S-SU-3 (rate-limit), S-SU-4 (honeypot).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.constants import TestConfig, make_email
from tests._core.err_msg import ErrMsg
from tests._core.response import expect_response
from tests._core.step import step
from tests.pages.signup_page import SignupPage
from tests.pages.verify_page import VerifyPage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@allure.title("Форма регистрации содержит обязательные поля и honeypot")
def test_signup_form_has_required_inputs(anon_pages: PageFactory, soft_check):
    """F-SU-1, X-SU-1..11: required inputs + autocomplete + honeypot tabindex."""
    signup = anon_pages.navigate_to(SignupPage)
    signup.expect_visible_form()
    signup.soft_check_form_basics(soft_check)


@allure.title("Успешная регистрация отправляет письмо с токеном верификации")
def test_signup_happy_path_sends_verification_email(page: Page, base_url: str, anon_pages: PageFactory):
    """F-SU-1, F-EV-1: submit form → backend sends verification email."""
    with step("действие: заполнение и отправка формы регистрации"):
        email = make_email("happy")
        signup = anon_pages.navigate_to(SignupPage)

        with page.expect_response("**/api/account/signup") as resp_info:
            signup.fill_required(
                email=email,
                password=TestConfig.DEFAULT_PASSWORD,
                full_name="Иванов Иван",
            ).submit()
        assert resp_info.value.status == 200, \
            f"signup endpoint returned {resp_info.value.status}"

        signup.expect_verification_message()

    with step("проверка: письмо с токеном верификации отправлено"):
        r = httpx.get(f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="last-email").status_ok()
        assert "token=" in (r.json()["text_body"] or ""), \
            f"no verification token in email: {r.json()!r}"


@allure.title("Подтверждение email автоматически авторизует пользователя")
def test_verify_email_auto_logs_in_via_set_cookie(page: Page, base_url: str, anon_pages: PageFactory):
    """TC-FLOW-1.1: POST /api/account/verify-email sets a session cookie in
    the response so the user is logged in immediately — no extra login step.

    Regression for UX-FLOW-002 (closed in commit 264db9e).
    """
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
            f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": email}
        )
        expect_response(mail, label="last-email").status_ok()
        m = re.search(r"token=([\w\-]+)", mail.json()["text_body"])
        assert m is not None, "verify token not found in email body"
        token = m.group(1)

    with step("действие: verify-email и проверка auto_login"):
        verify = httpx.post(
            f"{base_url}{API.VERIFY_EMAIL}", json={"token": token}
        )
        expect_response(verify, label="verify-email").status_ok()
        body = verify.json()
        assert body.get("auto_login") is True, \
            f"verify response must include auto_login=true: {body!r}"
        assert body.get("tenant_slug"), f"verify response missing tenant_slug: {body!r}"

    with step("проверка: session cookie установлена и /me доступен"):
        cookies = dict(verify.cookies)
        session_cookie = cookies.get("platform_session") or cookies.get("session_id")
        assert session_cookie, \
            f"verify-email response must Set-Cookie a session: got {list(cookies)}"

        me = httpx.get(f"{base_url}{API.ACCOUNT_ME}", cookies=cookies)
        expect_response(me, label="/me after verify").status_ok()
        assert me.json()["tenant"]["slug"] == body["tenant_slug"], \
            f"/me slug mismatch: expected {body['tenant_slug']!r}, got {me.json()['tenant']['slug']!r}"


@allure.title("После верификации email создаётся тенант для пользователя")
def test_signup_then_verify_creates_tenant(page: Page, base_url: str, anon_pages: PageFactory):
    """F-EV-4: after verify, login succeeds and tenant_slug is returned."""
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
            f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": email}
        )
        expect_response(mail, label="last-email").status_ok()
        m = re.search(r"token=([\w\-]+)", mail.json()["text_body"])
        assert m is not None, "verify token not found in email body"
        token = m.group(1)

    with step("действие: верификация email через UI"):
        anon_pages.create(VerifyPage).open_with_token(token).expect_success()

    with step("проверка: login возвращает tenant_slug"):
        me = httpx.post(
            f"{base_url}{API.LOGIN}",
            json={"email": email, "password": TestConfig.DEFAULT_PASSWORD},
        )
        expect_response(me, label="login after verify").status_ok()
        assert me.json()["tenant_slug"], f"no tenant_slug in login response: {me.json()}"


@allure.title("Заполненный honeypot даёт тихий 200 без отправки письма")
def test_honeypot_field_silently_succeeds(page: Page, base_url: str, anon_pages: PageFactory):
    """S-SU-4: filling honeypot 'website' → silent 200, no email captured.

    We wait for the signup response (no fixed sleep) and assert the
    backend treats it as silent success.
    """
    with step("действие: заполнение формы с honeypot и отправка"):
        email = make_email("bot")
        _ = anon_pages.navigate_to(SignupPage)
        page.evaluate(
            f"""
            document.querySelector('#email').value = {email!r};
            document.querySelector('#password').value = {TestConfig.DEFAULT_PASSWORD!r};
            document.querySelector('#website').value = 'http://spam.example.com';
            document.querySelector('#agreeTerms').checked = true;
            """
        )

        with page.expect_response("**/api/account/signup") as resp_info:
            page.locator("#signupBtn").click()
        assert resp_info.value.status == 200, \
            f"signup with honeypot returned {resp_info.value.status} (expected 200 silent)"

    with step("проверка: письмо не отправлено"):
        r = httpx.get(f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="honeypot: no email sent").status(404)


@allure.title("Одноразовый email отклоняется с ошибкой в поле ввода")
def test_disposable_email_rejected_inline(page: Page, base_url: str, anon_pages: PageFactory):
    """S-SU-5: disposable email — inline error visible, no email sent.

    Backend → 422 detail с подстрокой «email», и signup.html
    fallback-парсер находит slovo «email» → роутит ошибку в per-field
    `#email-err` (а не в общий `#signupMsg`). Это by design: чтобы SR
    + visual подсвечивали именно проблемное поле. Поэтому смотрим
    aria-invalid + текст внутри `#email-err`.
    """
    # Intentional non-`e2e.example.com` domain — `mailinator.com` is on the
    # backend's disposable-email blocklist, which is what this test exercises.
    with step("действие: попытка регистрации с одноразовым email"):
        disposable_email = "spam@mailinator.com"
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=disposable_email,
            password=TestConfig.DEFAULT_PASSWORD,
        ).submit()

    with step("проверка: inline-ошибка в поле email и письмо не отправлено"):
        email_err = page.locator("#email-err")
        expect(email_err, ErrMsg.wrong_text_content).not_to_have_text("")
        expect(page.locator("#email"), ErrMsg.wrong_attribute).to_have_attribute("aria-invalid", "true")

        r = httpx.get(f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": disposable_email})
        expect_response(r, label="disposable: no email sent").status(404)


@allure.title("Слишком короткий пароль не проходит валидацию формы")
def test_password_too_short_rejected_inline(page: Page, base_url: str, anon_pages: PageFactory):
    """S-SU-8: password < 8 chars — HTML5 validity blocks submit, no email sent."""
    with step("действие: попытка регистрации с коротким паролем"):
        email = make_email("shortpw")
        signup = anon_pages.navigate_to(SignupPage)
        signup.fill_required(
            email=email,
            password="123",
        ).submit()

    with step("проверка: HTML5 validation не пропускает и письмо не отправлено"):
        pwd_valid = page.evaluate("() => document.getElementById('password').checkValidity()")
        assert pwd_valid is False, \
            f"password input must fail HTML5 minlength validity, got {pwd_valid!r}"

        r = httpx.get(f"{base_url}{API.TEST_LAST_EMAIL}", params={"to": email})
        expect_response(r, label="short-pw: no email sent").status(404)
