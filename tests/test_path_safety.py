"""INV-PATH-001 regression-trail: malicious / malformed person IDs.

Backend treats `person_id` как opaque string в URL path. Run security
28.04 night confirmed defense-in-depth: bad ids → 404 (не 500, не leak).
"""

from __future__ import annotations

import pytest

from tests.api_paths import API


_MALICIOUS_IDS = [
    pytest.param("a" * 2000, id="very-long-2k-chars"),
    pytest.param("1' OR '1'='1", id="sqli-or-payload"),
    pytest.param("../../../etc/passwd", id="path-traversal"),
    pytest.param("__proto__", id="proto-pollution"),
]


@pytest.mark.parametrize("malicious_id", _MALICIOUS_IDS)
def test_malicious_person_id_returns_404_not_500(
    owner_user, tenant_client, malicious_id: str,
):
    """GET /api/people/{malicious_id} → 404, NOT 500."""
    api = tenant_client(owner_user)
    r = api.get(API.person(malicious_id))
    assert r.status_code != 500, (
        f"malicious id {malicious_id!r} crashed backend (500). "
        f"Body: {r.text[:300]}"
    )
    assert r.status_code in (400, 404, 422), (
        f"unexpected status for {malicious_id!r}: {r.status_code} {r.text[:200]}"
    )
