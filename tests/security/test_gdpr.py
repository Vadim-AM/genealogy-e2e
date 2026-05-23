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

import allure

from tests.api_paths import API
from tests.constants import unique_email
from tests.response import expect_response


@allure.title("GDPR: удаление тенанта инвалидирует сессию владельца")
def test_delete_tenant_invalidates_owner_session(
    signup_via_api, tenant_client,
):
    """INV-GDPR-001a: после soft-delete tenant'а старая cookie owner'а
    больше не должна работать на `/api/account/me`.

    Was xfail until upstream commit `771b1c0` ("fix(gdpr): invalidate
    sessions + login через deleting tenant"). Now plain regression.
    """
    user = signup_via_api(email=unique_email("gdpr"))
    api = tenant_client(user)

    # 1. Sanity: сессия валидна сейчас.
    expect_response(api.get(API.ACCOUNT_ME), label="pre-delete /me").status(200)

    # 2. POST delete-tenant — soft-delete с подтверждением через slug.
    r = api.post(API.DELETE_TENANT, json={"confirm_slug": user.slug})
    expect_response(r, label="delete-tenant").status(200)

    # 3. Cookie должна быть отозвана.
    me_after = api.get(API.ACCOUNT_ME)
    expect_response(me_after, label="INV-GDPR-001a: post-delete /me").status(401)
