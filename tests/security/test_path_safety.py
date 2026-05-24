"""INV-PATH-001 regression-trail: malicious / malformed person IDs."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import pytest

from api import routes
from assertions.base import should
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


_MALICIOUS_IDS = [
    pytest.param("a" * 2000, id="very-long-2k-chars"),
    pytest.param("1' OR '1'='1", id="sqli-or-payload"),
    pytest.param("../../../etc/passwd", id="path-traversal"),
    pytest.param("__proto__", id="proto-pollution"),
]


@pytest.mark.parametrize("malicious_id", _MALICIOUS_IDS)
@allure.title("Безопасность: вредоносный person ID возвращает 400/404, не 500")
def test_malicious_person_id_returns_404_not_500(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], malicious_id: str
) -> None:
    """GET /api/people/{malicious_id} → 404, NOT 500."""
    with step("действие: запросить person с вредоносным ID"):
        api = tenant_client(owner_user)
        r = api.get(routes.person(malicious_id))

    with step("проверка: статус 400/404/422, не 500"):
        should.not_equal(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection)
        expected = (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY)
        should.be_in(r.status_code, expected, ErrMsg.injection_status_unexpected)
