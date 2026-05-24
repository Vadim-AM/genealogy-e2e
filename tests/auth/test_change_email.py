"""INV-EMAIL-002: endpoint для смены email — initiation step."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Запрос смены email отправляет токен подтверждения на новый адрес")
def test_change_email_endpoint_initiates_confirmation(
    signup_via_api: Callable[..., AuthUser],
    tenant_client: Callable[[AuthUser], httpx.Client],
    read_email_token: Callable[[str], str],
) -> None:
    """INV-EMAIL-002: POST /api/account/me/email → 200 + confirmation mail."""
    with step("подготовка: signup и получение клиента"):
        user = signup_via_api(email=unique_email("orig"))
        api = tenant_client(user)

    with step("действие: запрос смены email"):
        new_email = unique_email("changed")
        r = api.post(
            routes.ACCOUNT_EMAIL,
            json={"new_email": new_email, "current_password": user.password},
        )

    with step("проверка: статус 200 и токен подтверждения отправлен"):
        expect_response(
            r,
            label="change-email should return 200/202 to initiate confirmation",
        ).status(HTTPStatus.OK)

        token = read_email_token(new_email)
        should.be_true(token, ErrMsg.change_email_token_missing)
