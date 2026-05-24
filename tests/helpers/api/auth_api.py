"""Typed wrappers for auth and account API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests._core.api_paths import API
from tests._core.response import expect_response
from tests._models.auth import AccountMe, InviteResponse

if TYPE_CHECKING:
    import httpx


def get_me(api: httpx.Client) -> AccountMe:
    """GET /api/account/me → AccountMe."""
    r = api.get(API.ACCOUNT_ME)
    return expect_response(r, label="account me").status_ok().schema(AccountMe)


def create_invite(api: httpx.Client, *, email: str | None = None, role: str = "viewer") -> InviteResponse:
    """POST /api/account/tenant/invites → InviteResponse."""
    payload: dict = {"role": role}
    if email:
        payload["email"] = email
    r = api.post(API.TENANT_INVITES, json=payload)
    return expect_response(r, label="create invite").status_ok().schema(InviteResponse)


def onboarding_reset(api: httpx.Client) -> None:
    """POST /api/account/onboarding-reset → assert 2xx."""
    r = api.post(API.ONBOARDING_RESET)
    expect_response(r, label="onboarding reset").status_ok()
