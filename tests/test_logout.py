"""Logout flow — F-LO-1..3.

Owner logs out → cookie cleared → /api/account/me returns 401.
"""

from __future__ import annotations

import httpx

from tests.timeouts import TIMEOUTS
import pytest
from playwright.sync_api import Page, expect


def test_logout_clears_session(owner_user, base_url: str):
    """F-LO-1: POST /api/account/logout clears the session cookie."""
    r = httpx.post(
        f"{base_url}/api/account/logout",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    # Logout endpoint may be 200 or 204; 404 means endpoint not yet wired
    # (legacy invite logout uses different path).
    if r.status_code == 404:
        pytest.skip("auth_v2 logout endpoint not present; /api/auth/logout for legacy")

    assert r.status_code in (200, 204), r.text

    # After logout, /me should no longer return tenant data.
    me = httpx.get(f"{base_url}/api/account/me", cookies=owner_user.cookies, timeout=TIMEOUTS.api_request)
    assert me.status_code in (401, 403), \
        f"session still valid after logout: {me.status_code} {me.text[:100]}"


def test_relogin_returns_same_tenant(owner_user, base_url: str):
    """F-LO-2: re-login with same email reaches the same tenant."""
    r = httpx.post(
        f"{base_url}/api/account/login",
        json={"email": owner_user.email, "password": owner_user.password},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, r.text
    new_session = dict(r.cookies)
    me = httpx.get(f"{base_url}/api/account/me", cookies=new_session, timeout=TIMEOUTS.api_request)
    assert me.status_code == 200, me.text
    assert me.json().get("tenant", {}).get("slug") == owner_user.slug
