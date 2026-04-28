"""Cross-tab session — TC-CROSS-1.

Two browser tabs share one session cookie. Logout in tab 0 must invalidate
the session for tab 1 — a subsequent /api/account/me call returns 401.
"""

from __future__ import annotations

import httpx

from tests.timeouts import TIMEOUTS


def test_logout_invalidates_session_across_tabs(
    auth_context_factory, owner_user, base_url: str
):
    """TC-CROSS-1: logout in one tab → /me 401 from another tab's cookies.

    We simulate two tabs by reusing the same `owner_user.cookies` in two
    httpx clients (cookie store is shared between browser tabs of the same
    profile/context — same as how the browser would behave).
    """
    # Tab 1 verifies an authenticated /me before we logout.
    me1 = httpx.get(
        f"{base_url}/api/account/me",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    me1.raise_for_status()
    assert me1.json()["tenant"]["slug"] == owner_user.slug

    # Tab 0 logs out (POST /api/account/logout consumes the same session).
    logout = httpx.post(
        f"{base_url}/api/account/logout",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert logout.status_code in (200, 204), \
        f"logout returned {logout.status_code} {logout.text[:200]}"

    # Tab 1 is now invalidated — /me returns 401 even though its cookie value
    # was set before the logout. This is server-side session revocation.
    me2 = httpx.get(
        f"{base_url}/api/account/me",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert me2.status_code == 401, \
        f"session still valid in tab 1 after tab 0 logout: " \
        f"{me2.status_code} {me2.text[:200]}"
