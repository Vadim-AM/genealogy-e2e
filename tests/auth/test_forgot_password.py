"""Forgot-password / reset-password — TC-FP-1..6.

End-to-end through UI: request reset → MockSender captures link → reset
form sets a new password → login works with the new password.
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page

from tests.api_paths import API
from tests.constants import make_email
from tests.pages.forgot_password_page import ForgotPasswordPage, ResetPasswordPage
from tests.timeouts import TIMEOUTS


def test_forgot_password_full_flow_changes_password(
    page: Page, base_url: str, owner_user, read_email_token
):
    """TC-FP-1, F-FP-1..6: forgot → reset email → new password → login OK."""
    fp = ForgotPasswordPage(page).goto()
    fp.expect_visible_form()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset(owner_user.email)
    assert resp_info.value.ok, f"forgot-password returned {resp_info.value.status}"
    fp.expect_success_message()

    token = read_email_token(owner_user.email)

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
        f"{base_url}{API.LOGIN}",
        json={"email": owner_user.email, "password": owner_user.password},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 401, \
        f"old password still works after reset: {r.status_code} {r.text[:200]}"

    # New password works.
    r = httpx.post(
        f"{base_url}{API.LOGIN}",
        json={"email": owner_user.email, "password": new_password},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["tenant_slug"] == owner_user.slug


def test_forgot_password_unknown_email_silent_200(page: Page, base_url: str):
    """F-FP-2 / TC-FP-2: anti-enumeration — request for unknown email returns
    silent 200 (UI shows the same success copy), no email captured.
    """
    unknown_email = make_email("never-registered")
    fp = ForgotPasswordPage(page).goto()
    with page.expect_response("**/api/account/forgot-password") as resp_info:
        fp.request_reset(unknown_email)
    assert resp_info.value.ok, \
        f"unknown-email request returned {resp_info.value.status} (must be silent 200)"
    fp.expect_success_message()

    # MockSender must not have captured anything for the unknown address.
    r = httpx.get(
        f"{base_url}{API.TEST_LAST_EMAIL}",
        params={"to": unknown_email},
        timeout=TIMEOUTS.api_short,
    )
    assert r.status_code == 404, "unknown email must not trigger a reset send"


def test_reset_password_token_is_single_use(
    base_url: str, owner_user, read_email_token,
):
    """F-FP-4 / TC-FP-4: re-using a reset token after success returns 400.

    Backend canonical contract for invalid/consumed token: 400 with a
    specific `detail` (no enumeration-leaking branches), not 401/410.
    """
    httpx.post(
        f"{base_url}{API.FORGOT_PASSWORD}",
        json={"email": owner_user.email},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    token = read_email_token(owner_user.email)

    new_password = "First_Reset_Password_2026"
    httpx.post(
        f"{base_url}{API.RESET_PASSWORD}",
        json={"token": token, "new_password": new_password},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    # Re-using the same token must fail with the canonical 400.
    r2 = httpx.post(
        f"{base_url}{API.RESET_PASSWORD}",
        json={"token": token, "new_password": "Another_Password_2026"},
        timeout=TIMEOUTS.api_request,
    )
    assert r2.status_code == 400, \
        f"reused reset token must return 400, got {r2.status_code} {r2.text[:200]}"
