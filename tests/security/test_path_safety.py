"""INV-PATH-001 regression-trail: malicious / malformed person IDs.

Backend treats `person_id` как opaque string в URL path. Run security
28.04 night confirmed defense-in-depth: bad ids → 404 (не 500, не leak).
"""

from __future__ import annotations

from http import HTTPStatus

import allure
import pytest

from api import routes
from framework.step import step

_MALICIOUS_IDS = [
    pytest.param("a" * 2000, id="very-long-2k-chars"),
    pytest.param("1' OR '1'='1", id="sqli-or-payload"),
    pytest.param("../../../etc/passwd", id="path-traversal"),
    pytest.param("__proto__", id="proto-pollution"),
]


@pytest.mark.parametrize("malicious_id", _MALICIOUS_IDS)
@allure.title("Безопасность: вредоносный person ID возвращает 400/404, не 500")
def test_malicious_person_id_returns_404_not_500(
    owner_user, tenant_client, malicious_id: str,
):
    """GET /api/people/{malicious_id} → 404, NOT 500."""
    with step("действие: запросить person с вредоносным ID"):
        api = tenant_client(owner_user)
        r = api.get(routes.person(malicious_id))

    with step("проверка: статус 400/404/422, не 500"):
        assert r.status_code != HTTPStatus.INTERNAL_SERVER_ERROR, (
            f"malicious id {malicious_id!r} crashed backend (500). "
            f"Body: {r.text[:300]}"
        )
        assert r.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY), (
            f"unexpected status for {malicious_id!r}: {r.status_code} {r.text[:200]}"
        )
