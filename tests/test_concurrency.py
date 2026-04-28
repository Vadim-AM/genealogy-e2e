"""INV-EDIT-001: lost update на concurrent PATCH.

Защита через optimistic concurrency: GET возвращает `ETag`, PATCH
принимает `If-Match`. Run security 28.04 night: ни ETag, ни If-Match
не реализованы. Этот тест проверяет MINIMAL контракт — наличие ETag
header в GET response. Полный optimistic-concurrency тест (412 на
mismatch) — отдельная история, требует точной координации.
"""

from __future__ import annotations

import pytest

from tests.api_paths import API
from tests.messages import TestData


@pytest.mark.xfail(
    reason="INV-EDIT-001: GET /api/people/{id} не возвращает ETag — "
           "concurrent PATCH ведут к lost update без warning. Run "
           "security 28.04. Fix: backend handler возвращает ETag "
           "(хеш updated_at + ключевых полей), PATCH handler "
           "принимает If-Match — иначе 412. См. RFC 7232.",
    strict=False,
)
def test_get_person_returns_etag_for_concurrency(owner_user, tenant_client):
    """INV-EDIT-001: GET /api/people/{id} returns an ETag header."""
    api = tenant_client(owner_user)
    r = api.get(API.person(TestData.DEMO_PERSON_ID))
    r.raise_for_status()
    etag = r.headers.get("etag") or r.headers.get("ETag")
    assert etag, (
        f"INV-EDIT-001: GET person missing ETag header. Concurrent "
        f"PATCH ведут к lost update без conflict-signal'а."
    )
