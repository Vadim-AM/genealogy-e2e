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

from tests.api_paths import API
from tests.constants import unique_email


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
    assert api.get(API.ACCOUNT_ME).status_code == 200

    # 2. POST delete-tenant — soft-delete с подтверждением через slug.
    r = api.post(API.DELETE_TENANT, json={"confirm_slug": user.slug})
    assert r.status_code in (200, 202, 204), (
        f"delete-tenant should succeed; got {r.status_code} {r.text[:200]}"
    )

    # 3. Cookie должна быть отозвана.
    me_after = api.get(API.ACCOUNT_ME)
    assert me_after.status_code in (401, 403), (
        f"INV-GDPR-001a: session NOT invalidated after delete-tenant. "
        f"Cookie returns {me_after.status_code} {me_after.text[:200]}. "
        f"Spec promises sessions are cleared on delete."
    )
