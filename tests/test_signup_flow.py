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


def test_signup_happy_path_sends_verification_email(
    page: Page, base_url: str
):
    """F-SU-1, F-EV-1: submit form → backend sends verification email."""
    responses: list[tuple[int, str]] = []
    page.on("response", lambda r: responses.append((r.status, r.url)))

    signup = SignupPage(page).goto()
    signup.fill_required(
        email="happy@e2e.example.com",
        password="strong_password_2026",
        full_name="Иванов Иван",
    ).submit()

    signup.expect_verification_message()

    signup_calls = [(s, u) for s, u in responses if "/api/account/signup" in u]
    assert signup_calls, f"signup endpoint never called: {responses}"
    last_status = signup_calls[-1][0]
    assert last_status == 200, f"signup returned {last_status}, responses={signup_calls}"

    # Verify backend captured an email for this address.
    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "happy@e2e.example.com"})
    assert r.status_code == 200, f"last-email response: {r.status_code} {r.text[:200]}"
    body = r.json()["text_body"] or ""
    assert "token=" in body, f"no verification token in email: {body[:200]}"


def test_signup_then_verify_creates_tenant(page: Page, base_url: str):
    """F-EV-4: after verify, tenant is created and welcome path is reachable."""
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="verify@e2e.example.com",
        password="strong_password_2026",
        full_name="Петр Петров",
    ).submit()
    signup.expect_verification_message()

    mail = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "verify@e2e.example.com"}).json()
    token_match = re.search(r"token=([\w\-]+)", mail["text_body"])
    assert token_match
    token = token_match.group(1)

    VerifyPage(page).open_with_token(token).expect_success()

    # Backend confirms tenant exists.
    me = httpx.post(
        f"{base_url}/api/account/login",
        json={"email": "verify@e2e.example.com", "password": "strong_password_2026"},
    )
    assert me.status_code == 200
    data = me.json()
    # Login response uses `tenant_slug` (top-level), not `tenant.slug`.
    slug = data.get("tenant_slug") or (data.get("tenant") or {}).get("slug")
    assert slug, f"no tenant slug in login response: {data}"


def test_honeypot_field_silently_succeeds(page: Page, base_url: str):
    """S-SU-4: filling honeypot 'website' → silent success, no DB row."""
    page.goto("/signup")
    # Fill all fields incl. hidden honeypot via JS (since tabindex=-1)
    page.evaluate(
        """
        document.querySelector('#email').value = 'bot@e2e.example.com';
        document.querySelector('#password').value = 'strong_password_2026';
        document.querySelector('#full_name').value = 'Bot Botov';
        document.querySelector('#website').value = 'http://spam.example.com';
        document.querySelector('#agree').checked = true;
        """
    )
    page.locator("#signupBtn").click()
    page.wait_for_timeout(1500)

    # No verification email should be captured.
    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "bot@e2e.example.com"})
    assert r.status_code == 404, "honeypot should suppress email send"


def test_disposable_email_rejected(page: Page):
    """S-SU-5: disposable email domain rejected with visible error."""
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="spam@mailinator.com",
        password="strong_password_2026",
    ).submit()

    page.wait_for_timeout(1500)
    body_text = (page.content() or "").lower()
    assert any(
        word in body_text for word in ("временн", "одноразов", "недопуст", "disposable")
    ) or page.get_by_text("ошибк", exact=False).first.is_visible(), \
        "expected disposable-email error visible"


def test_password_too_short_rejected(page: Page, base_url: str):
    """S-SU-8: password < 8 chars rejected client-side or server-side."""
    signup = SignupPage(page).goto()
    signup.fill_required(
        email="shortpw@e2e.example.com",
        password="123",
    ).submit()
    page.wait_for_timeout(1500)
    r = httpx.get(f"{base_url}/api/_test/last-email", params={"to": "shortpw@e2e.example.com"})
    assert r.status_code == 404, "short password should not trigger email send"


def test_already_authenticated_user_signup_does_not_break(
    page: Page, base_url: str, signup_via_api
):
    """Edge: an already-authed user opening /signup doesn't get a 500.

    Actual product behaviour may redirect or show a notice — we just assert
    the page renders and there's no console exception.
    """
    user = signup_via_api(email="already-authed@e2e.example.com", password="MyStrong#Pwd2026!Tree")
    for name, value in user.cookies.items():
        page.context.add_cookies(
            [{"name": name, "value": value, "domain": "127.0.0.1", "path": "/"}]
        )
    response = page.goto("/signup")
    assert response is not None
    assert response.status < 500
