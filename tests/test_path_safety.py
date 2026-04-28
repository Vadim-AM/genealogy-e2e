"""INV-PATH-001 regression-trail: malicious / malformed person IDs.

Backend treats `person_id` as an opaque string in URL path. Run
security 28.04 night confirmed defense-in-depth — все вредные
варианты возвращают 404 (не 500, не data leak):

- очень длинный id (> 1000 chars)
- SQLi-like payload (`1' OR '1'='1`)
- path traversal `..`
- `__proto__` (JS prototype pollution attempt)
- trailing slash

Тест passing — это **regression-trail**, защищает контракт «bad
id → 404 без crash» от будущих регрессий.
"""

from __future__ import annotations

import httpx
import pytest

from tests.timeouts import TIMEOUTS


_MALICIOUS_IDS = [
    pytest.param("a" * 2000, id="very-long-2k-chars"),
    pytest.param("1' OR '1'='1", id="sqli-or-payload"),
    pytest.param("../../../etc/passwd", id="path-traversal"),
    pytest.param("__proto__", id="proto-pollution"),
]


@pytest.mark.parametrize("malicious_id", _MALICIOUS_IDS)
def test_malicious_person_id_returns_404_not_500(
    owner_user, base_url: str, malicious_id: str
):
    """GET /api/people/{malicious_id} → 404, NOT 500.

    Закрывает целую серию security-paths одной param-секцией.
    """
    r = httpx.get(
        f"{base_url}/api/people/{malicious_id}",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code != 500, (
        f"malicious id {malicious_id!r} crashed backend (500). "
        f"Body: {r.text[:300]}"
    )
    assert r.status_code in (400, 404, 422), (
        f"unexpected status for {malicious_id!r}: {r.status_code} {r.text[:200]}"
    )
