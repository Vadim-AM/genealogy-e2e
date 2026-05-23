"""Session invalidation helpers — password reset flow + status check."""

from __future__ import annotations

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS

NEW_PASSWORD = "NewPassword_After_Reset_2026"


def me_status(base_url: str, cookies: dict[str, str]) -> int:
    return httpx.get(
        f"{base_url}{API.ACCOUNT_ME}",
        cookies=cookies,
        timeout=TIMEOUTS.api_request,
    ).status_code


def trigger_password_reset(
    base_url: str, *, email: str, new_password: str, read_email_token,
) -> None:
    """forgot-password -> read token from mail -> reset-password."""
    httpx.post(
        f"{base_url}{API.FORGOT_PASSWORD}",
        json={"email": email},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    token = read_email_token(email)
    httpx.post(
        f"{base_url}{API.RESET_PASSWORD}",
        json={"token": token, "new_password": new_password},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
