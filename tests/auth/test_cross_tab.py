"""Cross-tab session — TC-CROSS-1.

Two browser tabs share one session cookie. Logout in tab 0 must invalidate
the session for tab 1 — a subsequent /api/account/me call returns 401.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from tests._core import api_paths as routes
from tests._core.step import step


@allure.title("Выход из одной вкладки инвалидирует сессию в другой")
def test_logout_invalidates_session_across_tabs(owner_user, tenant_client):
    """TC-CROSS-1: logout in one tab → /me 401 from another tab's cookies.

    We simulate two tabs by reusing the same `owner_user.cookies` in two
    httpx clients (cookie store is shared between browser tabs of the same
    profile/context — same as how the browser would behave).
    """
    with step("подготовка: создание двух вкладок с общей сессией"):
        tab1 = tenant_client(owner_user)
        tab0 = tenant_client(owner_user)

    with step("проверка: сессия tab1 активна до logout"):
        me1 = tab1.get(routes.ACCOUNT_ME)
        me1.raise_for_status()
        assert me1.json()["tenant"]["slug"] == owner_user.slug, \
            f"session should belong to {owner_user.slug!r}, got {me1.json()['tenant']['slug']!r}"

    with step("действие: logout из tab0"):
        logout = tab0.post(routes.LOGOUT)
        assert logout.status_code == HTTPStatus.OK, \
            f"logout returned {logout.status_code} {logout.text[:200]}"

    with step("проверка: сессия tab1 инвалидирована после logout tab0"):
        # Tab 1 is now invalidated — server-side session revocation kills the
        # cookie that was minted before the logout even though the cookie value
        # itself hasn't changed.
        me2 = tab1.get(routes.ACCOUNT_ME)
        assert me2.status_code == HTTPStatus.UNAUTHORIZED, \
            f"session still valid in tab 1 after tab 0 logout: " \
            f"{me2.status_code} {me2.text[:200]}"
