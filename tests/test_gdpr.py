"""GDPR / 152-ФЗ обязательства — INV-GDPR-001a.

После запроса на удаление tenant'а / right-to-erasure пользователь
ожидает, что:
1. Сессия немедленно завершается (cookie невалидна — `/me` 401).
2. Через 30-day grace восстановление возможно по email + новый
   login.

Run security 28.04 night показал:
- INV-GDPR-001a: после `/api/account/delete-tenant` старая cookie
  владельца **остаётся валидной** — `/api/account/me` возвращает
  200 с данными «удалённого» tenant'а. Пользователь видит свой
  tenant как ни в чём не бывало (несмотря на UI «удалено»).
- INV-GDPR-001b: восстановление в 30-day grace через login → 403
  («tenant deleted»), и нет flow «верните мой tenant».

Здесь покрывается **GDPR-001a** — простой flow. **001b** требует
более сложный 30-day setup и пока не автоматизируется.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"


@pytest.mark.xfail(
    reason="INV-GDPR-001a: POST /api/account/delete-tenant не отзывает "
           "active session — owner'а cookie всё ещё валидна, /me 200. "
           "Run security 28.04 night. Spec пишет «сессия зачищается». "
           "Compliance trap: пользователь думает, что удалил аккаунт + "
           "сессию, фактически сессия активна. Fix: при /delete-tenant "
           "удалить все PlatformSession для user_id (как мы сделали "
           "для INV-AUTH-001 в reset-password — same pattern).",
    strict=False,
)
def test_delete_tenant_invalidates_owner_session(
    signup_via_api, base_url: str
):
    """INV-GDPR-001a: после soft-delete tenant'а старая cookie owner'а
    больше не должна работать на `/api/account/me`."""
    email = f"gdpr-{uuid.uuid4().hex[:8]}@e2e.example.com"
    user = signup_via_api(email=email)

    # 1. Sanity: сессия валидна сейчас.
    me_before = httpx.get(
        f"{base_url}/api/account/me",
        cookies=user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert me_before.status_code == 200

    # 2. POST delete-tenant — soft-delete с подтверждением через slug.
    r = httpx.post(
        f"{base_url}/api/account/delete-tenant",
        json={"confirm_slug": user.slug},
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )
    # delete-tenant сам должен вернуть 200/204 (или 202 если async).
    assert r.status_code in (200, 202, 204), (
        f"delete-tenant should succeed; got {r.status_code} {r.text[:200]}"
    )

    # 3. Cookie должна быть отозвана — /me возвращает 401.
    me_after = httpx.get(
        f"{base_url}/api/account/me",
        cookies=user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert me_after.status_code in (401, 403), (
        f"INV-GDPR-001a: session NOT invalidated after delete-tenant. "
        f"Cookie returns {me_after.status_code} {me_after.text[:200]}. "
        f"Spec promises sessions are cleared on delete."
    )
