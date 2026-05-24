"""Cross-tab session — TC-CROSS-1."""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg


@allure.title("Выход из одной вкладки инвалидирует сессию в другой")
def test_logout_invalidates_session_across_tabs(owner_user, tenant_client) -> None:
    """TC-CROSS-1: logout в одной вкладке → /me 401 из другой."""
    with step("подготовка: создание двух вкладок с общей сессией"):
        tab1 = tenant_client(owner_user)
        tab0 = tenant_client(owner_user)

    with step("проверка: сессия tab1 активна до logout"):
        me1 = tab1.get(routes.ACCOUNT_ME)
        me1.raise_for_status()
        should.be_equal(me1.json()["tenant"]["slug"], owner_user.slug, ErrMsg.cross_tab_slug_mismatch)

    with step("действие: logout из tab0"):
        logout = tab0.post(routes.LOGOUT)
        expect_response(logout, label="logout").status(HTTPStatus.OK)

    with step("проверка: сессия tab1 инвалидирована после logout tab0"):
        me2 = tab1.get(routes.ACCOUNT_ME)
        expect_response(
            me2, label="session still valid in tab 1 after tab 0 logout",
        ).status(HTTPStatus.UNAUTHORIZED)
