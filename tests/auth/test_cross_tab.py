"""Cross-tab session — TC-CROSS-1.

Two browser tabs share one session cookie. Logout in tab 0 must invalidate
the session for tab 1 — a subsequent /api/account/me call returns 401.
"""

from __future__ import annotations

from tests.api_paths import API


def test_logout_invalidates_session_across_tabs(owner_user, tenant_client):
    """TC-CROSS-1: logout in one tab → /me 401 from another tab's cookies.

    We simulate two tabs by reusing the same `owner_user.cookies` in two
    httpx clients (cookie store is shared between browser tabs of the same
    profile/context — same as how the browser would behave).
    """
    tab1 = tenant_client(owner_user)
    tab0 = tenant_client(owner_user)

    me1 = tab1.get(API.ACCOUNT_ME)
    me1.raise_for_status()
    assert me1.json()["tenant"]["slug"] == owner_user.slug, \
        f"session should belong to {owner_user.slug!r}, got {me1.json()['tenant']['slug']!r}"

    logout = tab0.post(API.LOGOUT)
    assert logout.status_code == 200, \
        f"logout returned {logout.status_code} {logout.text[:200]}"

    # Tab 1 is now invalidated — server-side session revocation kills the
    # cookie that was minted before the logout even though the cookie value
    # itself hasn't changed.
    me2 = tab1.get(API.ACCOUNT_ME)
    assert me2.status_code == 401, \
        f"session still valid in tab 1 after tab 0 logout: " \
        f"{me2.status_code} {me2.text[:200]}"
