"""INV-EDIT-001: наличие ETag header для контроля конкурентности."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("GET персоны возвращает ETag для контроля конкурентности")
def test_get_person_returns_etag_for_concurrency(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """GET /api/people/{id} возвращает ETag header."""
    with step("действие: GET person"):
        api = tenant_client(owner_user)
        r = api.get(routes.person(TestData.DEMO_PERSON_ID))
        expect_response(r, label="GET person").status_ok()

    with step("проверка: ETag header присутствует"):
        etag = r.headers.get("etag")
        should.be_true(etag, ErrMsg.etag_missing)
