"""GDPR / 152-ФЗ обязательства — INV-GDPR-001a."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from models.auth import AccountMe

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("GDPR: удаление тенанта инвалидирует сессию владельца")
def test_delete_tenant_invalidates_owner_session(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """INV-GDPR-001a: после soft-delete tenant'а старая cookie owner'а."""
    with step("подготовка: создать пользователя и проверить валидность сессии"):
        user = signup_via_api(email=unique_email("gdpr"))
        api = tenant_client(user)
        expect_response(api.get(routes.ACCOUNT_ME), label="pre-delete /me").status_ok().schema(AccountMe)

    with step("действие: удалить тенант через soft-delete"):
        r = api.post(routes.DELETE_TENANT, json={"confirm_slug": user.slug})
        expect_response(r, label="delete-tenant").status_ok()

    with step("проверка: cookie отозвана, /me возвращает 401"):
        me_after = api.get(routes.ACCOUNT_ME)
        expect_response(me_after, label="INV-GDPR-001a: post-delete /me").status(HTTPStatus.UNAUTHORIZED)
