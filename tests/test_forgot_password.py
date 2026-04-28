"""Forgot-password / reset-password — TC-FP-1..6.

End-to-end through UI: request reset → MockSender captures link → reset
form sets a new password → login works with the new password.
"""

from __future__ import annotations

import re

import httpx
from playwright.sync_api import Page, expect

from tests.pages.forgot_password_page import ForgotPasswordPage, ResetPasswordPage
from tests.pages.login_page import LoginPage
from tests.timeouts import TIMEOUTS


def test_forgot_password_full_flow_changes_password(
    page: Page, base_url: str, owner_user
):
    """TC-FP-1, F-FP-1..6: forgot → reset email → new password → login OK."""
    fp = ForgotPasswordPage(page).goto()
    fp.expect_visible_form()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset(owner_user.email)
    assert resp_info.value.ok, f"forgot-password returned {resp_info.value.status}"
    fp.expect_success_message()

    # MockSender now has a reset email with a `?token=...` link.
    mail = httpx.get(
        f"{base_url}/api/_test/last-email",
        params={"to": owner_user.email},
        timeout=TIMEOUTS.api_short,
    )
    mail.raise_for_status()
    body = mail.json()["text_body"] or ""
    token_match = re.search(r"token=([\w\-]+)", body)
    assert token_match, f"no reset token in email: {body[:200]}"
    token = token_match.group(1)

    new_password = "Brand_New_Password_2026"
    rp = ResetPasswordPage(page).open_with_token(token)
    with page.expect_response("**/api/account/reset-password") as resp_info:
        rp.submit_new_password(new_password)
    assert resp_info.value.ok, f"reset-password returned {resp_info.value.status}"
    rp.expect_success_message()

    # The page redirects to /login after ~1500ms — wait for that.
    page.wait_for_url("**/login")

    # Old password no longer works.
    r = httpx.post(
        f"{base_url}/api/account/login",
        json={"email": owner_user.email, "password": owner_user.password},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 401, \
        f"old password still works after reset: {r.status_code} {r.text[:200]}"

    # New password works.
    r = httpx.post(
        f"{base_url}/api/account/login",
        json={"email": owner_user.email, "password": new_password},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["tenant_slug"] == owner_user.slug


def test_forgot_password_unknown_email_silent_200(page: Page, base_url: str):
    """F-FP-2 / TC-FP-2: anti-enumeration — request for unknown email returns
    silent 200 (UI shows the same success copy), no email captured.
    """
    fp = ForgotPasswordPage(page).goto()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset("never-registered@e2e.example.com")
    assert resp_info.value.ok, \
        f"unknown-email request returned {resp_info.value.status} (must be silent 200)"
    fp.expect_success_message()

    # MockSender must not have captured anything for the unknown address.
    r = httpx.get(
        f"{base_url}/api/_test/last-email",
        params={"to": "never-registered@e2e.example.com"},
        timeout=TIMEOUTS.api_short,
    )
    assert r.status_code == 404, "unknown email must not trigger a reset send"


def test_reset_password_token_is_single_use(
    page: Page, base_url: str, owner_user
):
    """F-FP-4 / TC-FP-4: re-using a reset token after success returns 4xx,
    not another success."""
    # Step 1: trigger and consume the token via API (faster than UI for setup).
    httpx.post(
        f"{base_url}/api/account/forgot-password",
        json={"email": owner_user.email},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    mail = httpx.get(
        f"{base_url}/api/_test/last-email",
        params={"to": owner_user.email},
        timeout=TIMEOUTS.api_short,
    ).json()
    token = re.search(r"token=([\w\-]+)", mail["text_body"]).group(1)

    new_password = "First_Reset_Password_2026"
    r = httpx.post(
        f"{base_url}/api/account/reset-password",
        json={"token": token, "new_password": new_password},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()

    # Step 2: re-using the same token must fail with a 4xx.
    r2 = httpx.post(
        f"{base_url}/api/account/reset-password",
        json={"token": token, "new_password": "Another_Password_2026"},
        timeout=TIMEOUTS.api_request,
    )
    assert 400 <= r2.status_code < 500, \
        f"reused reset token must 4xx, got {r2.status_code} {r2.text[:200]}"
