"""INV-EDIT-001: lost update на concurrent PATCH.

Защита через optimistic concurrency: GET возвращает `ETag`, PATCH
принимает `If-Match`. Run security 28.04 night: ни ETag, ни If-Match
не реализованы. Этот тест проверяет MINIMAL контракт — наличие ETag
header в GET response. Полный optimistic-concurrency тест (412 на
mismatch) — отдельная история, требует точной координации.
"""

from __future__ import annotations

import allure

from tests._core.api_paths import API
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step


@allure.title("GET персоны возвращает ETag для контроля конкурентности")
def test_get_person_returns_etag_for_concurrency(owner_user, tenant_client):
    """INV-EDIT-001: GET /api/people/{id} returns an ETag header.

    Was xfail until upstream batch-6/7. Now regular regression.
    """
    with step("действие: GET person"):
        api = tenant_client(owner_user)
        r = api.get(API.person(TestData.DEMO_PERSON_ID))
        expect_response(r, label="GET person").status_ok()

    with step("проверка: ETag header присутствует"):
        etag = r.headers.get("etag")
        assert etag, (
            "INV-EDIT-001: GET person missing ETag header. Concurrent "
            "PATCH ведут к lost update без conflict-signal'а."
        )
