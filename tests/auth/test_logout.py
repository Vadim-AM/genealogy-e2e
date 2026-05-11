"""Logout flow — F-LO-1..3.

Owner logs out → cookie cleared → /api/account/me returns 401.
"""

from __future__ import annotations

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


def test_logout_clears_session(owner_user, tenant_client):
    """F-LO-1: POST /api/account/logout clears the session cookie.

    Backend contract: 204 on success. Subsequent /me with the dead cookie
    returns 401 (server-side session was invalidated even though the
    client-side cookie value is unchanged).
    """
    api = tenant_client(owner_user)

    r = api.post(API.LOGOUT)
    assert r.status_code == 204, (
        f"logout endpoint returned {r.status_code}; expected 204. "
        f"404 here means /api/account/logout was unwired — that's a regression, "
        f"not «scenario doesn't apply». Body: {r.text[:200]}"
    )

    me = api.get(API.ACCOUNT_ME)
    assert me.status_code == 401, \
        f"session still valid after logout: {me.status_code} {me.text[:100]}"


def test_relogin_returns_same_tenant(owner_user, base_url: str):
    """F-LO-2: re-login with same email reaches the same tenant.

    Login is anonymous (no auth needed to issue a session), so we use
    a plain client rather than `tenant_client`.
    """
    r = httpx.post(
        f"{base_url}{API.LOGIN}",
        json={"email": owner_user.email, "password": owner_user.password},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, r.text
    new_session = dict(r.cookies)
    me = httpx.get(
        f"{base_url}{API.ACCOUNT_ME}",
        cookies=new_session,
        timeout=TIMEOUTS.api_request,
    )
    assert me.status_code == 200, me.text
    assert me.json().get("tenant", {}).get("slug") == owner_user.slug
