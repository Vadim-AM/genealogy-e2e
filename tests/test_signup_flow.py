"""Signup + email verification flow (этапы 1-2 funnel).

Covers: F-SU-1..7, X-SU-1..11, F-EV-1..8, S-SU-3 (rate-limit), S-SU-4 (honeypot).
"""

from __future__ import annotations

import re

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.pages.signup_page import SignupPage
from tests.pages.verify_page import VerifyPage


def test_signup_form_has_required_inputs(page: Page, soft_check):
    """F-SU-1, X-SU-1..11: required inputs + autocomplete + honeypot tabindex."""
    signup = SignupPage(page).goto()
    signup.expect_visible_form()
    signup.soft_check_form_basics(soft_check)


def test_signup_happy_path_sends_verification_email(page: Page, base_url: str):
    """F-SU-1, F-EV-1: submit form → backend sends verification email."""
    signup = SignupPage(page).goto()

    with page.expect_response("**/api/account/signup") as resp_info:
        signup.fill_required(
            email="happy@e2e.example.com",
            password="strong_password_2026",
            full_name="Иванов Иван",
        ).submit()
    assert resp_info.value.status == 200, \
        f"signup endpoint returned {resp_info.value.status}"

    signup.expect_verification_message()

    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "happy@e2e.example.com"})
    r.raise_for_status()
    assert "token=" in (r.json()["text_body"] or ""), \
        f"no verification token in email: {r.json()!r}"


def test_verify_email_auto_logs_in_via_set_cookie(page: Page, base_url: str):
    """TC-FLOW-1.1: POST /api/account/verify-email sets a session cookie in
    the response so the user is logged in immediately — no extra login step.

    Regression for UX-FLOW-002 (closed in commit 264db9e).
    """
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="autologin@e2e.example.com",
        password="strong_password_2026",
        full_name="Автологин Тестов",
    ).submit()
    signup.expect_verification_message()

    mail = httpx.get(
        f"{base_url}/api/_test/last-email", params={"to": "autologin@e2e.example.com"}
    )
    mail.raise_for_status()
    token = re.search(r"token=([\w\-]+)", mail.json()["text_body"]).group(1)

    # POST /verify-email directly — checking that the response carries a
    # session cookie + the auto_login=true contract.
    verify = httpx.post(
        f"{base_url}/api/account/verify-email", json={"token": token}
    )
    verify.raise_for_status()
    body = verify.json()
    assert body.get("auto_login") is True, \
        f"verify response must include auto_login=true: {body!r}"
    assert body.get("tenant_slug"), f"verify response missing tenant_slug: {body!r}"

    cookies = dict(verify.cookies)
    session_cookie = cookies.get("platform_session") or cookies.get("session_id")
    assert session_cookie, \
        f"verify-email response must Set-Cookie a session: got {list(cookies)}"

    # The cookie alone (no separate login call) should authenticate /me.
    me = httpx.get(f"{base_url}/api/account/me", cookies=cookies)
    me.raise_for_status()
    assert me.json()["tenant"]["slug"] == body["tenant_slug"]


def test_signup_then_verify_creates_tenant(page: Page, base_url: str):
    """F-EV-4: after verify, login succeeds and tenant_slug is returned."""
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="verify@e2e.example.com",
        password="strong_password_2026",
        full_name="Петр Петров",
    ).submit()
    signup.expect_verification_message()

    mail = httpx.get(
        f"{base_url}/api/_test/last-email", params={"to": "verify@e2e.example.com"}
    )
    mail.raise_for_status()
    token = re.search(r"token=([\w\-]+)", mail.json()["text_body"]).group(1)

    VerifyPage(page).open_with_token(token).expect_success()

    me = httpx.post(
        f"{base_url}/api/account/login",
        json={"email": "verify@e2e.example.com", "password": "strong_password_2026"},
    )
    me.raise_for_status()
    assert me.json()["tenant_slug"], f"no tenant_slug in login response: {me.json()}"


def test_honeypot_field_silently_succeeds(page: Page, base_url: str):
    """S-SU-4: filling honeypot 'website' → silent 200, no email captured.

    We wait for the signup response (no fixed sleep) and assert the
    backend treats it as silent success.
    """
    page.goto("/signup")
    # P0.4 (ФЗ-156): 3 раздельных consent + honeypot. Поле full_name
    # удалено в commit 814d5f8 — его в DOM нет.
    page.evaluate(
        """
        document.querySelector('#email').value = 'bot@e2e.example.com';
        document.querySelector('#password').value = 'strong_password_2026';
        document.querySelector('#website').value = 'http://spam.example.com';
        document.querySelector('#agreeTerms').checked = true;
        document.querySelector('#agreePrivacy').checked = true;
        document.querySelector('#agreeCrossBorder').checked = true;
        """
    )

    with page.expect_response("**/api/account/signup") as resp_info:
        page.locator("#signupBtn").click()
    assert resp_info.value.status == 200, \
        f"signup with honeypot returned {resp_info.value.status} (expected 200 silent)"

    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "bot@e2e.example.com"})
    assert r.status_code == 404, "honeypot should suppress email send"


def test_disposable_email_rejected_inline(page: Page, base_url: str):
    """S-SU-5: disposable email — inline error visible, no email sent.

    Backend → 422 detail с подстрокой «email», и signup.html
    fallback-парсер находит slovo «email» → роутит ошибку в per-field
    `#email-err` (а не в общий `#signupMsg`). Это by design: чтобы SR
    + visual подсвечивали именно проблемное поле. Поэтому смотрим
    aria-invalid + текст внутри `#email-err`.
    """
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="spam@mailinator.com",
        password="strong_password_2026",
    ).submit()

    email_err = page.locator("#email-err")
    expect(email_err).not_to_have_text("")
    expect(page.locator("#email")).to_have_attribute("aria-invalid", "true")

    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "spam@mailinator.com"})
    assert r.status_code == 404, "disposable email must not trigger verification send"


def test_password_too_short_rejected_inline(page: Page, base_url: str):
    """S-SU-8: password < 8 chars — HTML5 validity blocks submit, no email sent."""
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="shortpw@e2e.example.com",
        password="123",
    ).submit()

    pwd_valid = page.evaluate("() => document.getElementById('password').checkValidity()")
    assert pwd_valid is False, "password input must fail HTML5 minlength validity"

    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "shortpw@e2e.example.com"})
    assert r.status_code == 404, "rejected password must not trigger verification send"
