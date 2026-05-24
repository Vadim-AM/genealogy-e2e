"""Session invalidation helpers — password reset flow + status check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from api import routes

if TYPE_CHECKING:
    from collections.abc import Callable

NEW_PASSWORD = "NewPassword_After_Reset_2026"


def me_status(base_url: str, cookies: dict[str, str]) -> int:
    """Return HTTP status code of GET /api/account/me."""
    return httpx.get(
        f"{base_url}{routes.ACCOUNT_ME}",
        cookies=cookies,
    ).status_code


def trigger_password_reset(
    base_url: str, *, email: str, new_password: str, read_email_token: Callable[[str], str],
) -> None:
    """forgot-password -> read token from mail -> reset-password."""
    httpx.post(
        f"{base_url}{routes.FORGOT_PASSWORD}",
        json={"email": email},
    ).raise_for_status()
    token = read_email_token(email)
    httpx.post(
        f"{base_url}{routes.RESET_PASSWORD}",
        json={"token": token, "new_password": new_password},
    ).raise_for_status()
