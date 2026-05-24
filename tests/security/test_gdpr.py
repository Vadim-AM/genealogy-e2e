"""GDPR / 152-ФЗ обязательства — INV-GDPR-001a.

После запроса на удаление tenant'а пользователь ожидает, что
сессия немедленно завершается. Run security 28.04 night показал:
после `/api/account/delete-tenant` старая cookie владельца **остаётся
валидной** — `/api/account/me` возвращает 200 с данными «удалённого»
tenant'а. Spec пишет «сессия зачищается» — не зачищается.

INV-GDPR-001b (восстановление в 30-day grace) требует более сложный
setup и пока не автоматизируется.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import routes
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from models.auth import AccountMe


@allure.title("GDPR: удаление тенанта инвалидирует сессию владельца")
def test_delete_tenant_invalidates_owner_session(
    signup_via_api, tenant_client,
) -> None:
    """INV-GDPR-001a: после soft-delete tenant'а старая cookie owner'а
    больше не должна работать на `/api/account/me`.

    Was xfail until upstream commit `771b1c0` ("fix(gdpr): invalidate
    sessions + login через deleting tenant"). Now plain regression.
    """
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
