"""INV-AUTH-001 + INV-MULTIDEVICE-001a: reset password инвалидирует сессии."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from assertions.base import should
from config.constants import unique_email
from framework.step import step
from helpers.auth.session_helpers import NEW_PASSWORD, me_status, trigger_password_reset
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


@allure.title("Сброс пароля инвалидирует текущую активную сессию")
def test_password_reset_invalidates_active_session(
    signup_via_api: Callable[..., AuthUser], read_email_token: Callable[[str], str], base_url: str
) -> None:
    """INV-AUTH-001: после reset-password старая session cookie отзывается (401)."""
    with step("подготовка: signup и проверка активной сессии"):
        email = unique_email("sess")
        user = signup_via_api(email=email)
        should.be_equal(me_status(base_url, user.cookies), HTTPStatus.OK, ErrMsg.session_should_be_active)

    with step("действие: сброс пароля"):
        trigger_password_reset(
            base_url,
            email=email,
            new_password=NEW_PASSWORD,
            read_email_token=read_email_token,
        )

    with step("проверка: старая сессия инвалидирована (401)"):
        should.be_equal(
            me_status(base_url, user.cookies),
            HTTPStatus.UNAUTHORIZED,
            ErrMsg.session_not_invalidated,
        )


@allure.title("Сброс пароля отзывает сессии на всех устройствах")
def test_password_reset_invalidates_all_devices_sessions(
    signup_via_api: Callable[..., AuthUser],
    login_existing: Callable[..., dict[str, str]],
    read_email_token: Callable[[str], str],
    base_url: str,
) -> None:
    """INV-MULTIDEVICE-001a: все sessions user'а отзываются при reset-password."""
    with step("подготовка: signup и создание двух параллельных сессий"):
        email = unique_email("mdev")
        user = signup_via_api(email=email)
        device_a_cookies = user.cookies
        device_b_cookies = login_existing(email)

    with step("подготовка: проверка что обе сессии активны"):
        should.be_equal(me_status(base_url, device_a_cookies), HTTPStatus.OK, ErrMsg.session_should_be_active)
        should.be_equal(me_status(base_url, device_b_cookies), HTTPStatus.OK, ErrMsg.session_should_be_active)

    with step("действие: сброс пароля"):
        trigger_password_reset(
            base_url,
            email=email,
            new_password=NEW_PASSWORD,
            read_email_token=read_email_token,
        )

    with step("проверка: сессия device A инвалидирована (401)"):
        should.be_equal(
            me_status(base_url, device_a_cookies),
            HTTPStatus.UNAUTHORIZED,
            ErrMsg.session_not_invalidated,
        )
