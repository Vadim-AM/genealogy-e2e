"""INV-GEDCOM-001: GEDCOM endpoints not migrated to auth_v2.

Was xfail until upstream commit `17d11b1` ("fix(auth): bridge auth_v2
owner для photos и GEDCOM"). Now plain regression — auth_v2 owner
может export/import без legacy admin password.
"""

from __future__ import annotations

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


def test_owner_can_export_gedcom_via_auth_v2(owner_user, tenant_client):
    """INV-GEDCOM-001 (export): auth_v2 owner получает 200 + GEDCOM body."""
    api = tenant_client(owner_user)
    r = api.get(API.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)
    assert r.status_code == 200, (
        f"GEDCOM export not accessible to auth_v2 owner: "
        f"{r.status_code} {r.text[:200]}"
    )
    # GEDCOM-формат начинается с '0 HEAD'.
    assert b"0 HEAD" in r.content[:200] or "0 HEAD" in r.text[:200], (
        f"response is not a GEDCOM file: starts with {r.content[:80]!r}"
    )


def test_owner_can_import_gedcom_via_auth_v2(owner_user, tenant_client):
    """INV-GEDCOM-001 (import): auth_v2 owner может POST GEDCOM."""
    api = tenant_client(owner_user)
    minimal_gedcom = (
        "0 HEAD\n"
        "1 SOUR Genealogy-e2e\n"
        "0 @I1@ INDI\n"
        "1 NAME Тестовый /Импорт/\n"
        "0 TRLR\n"
    )
    r = api.post(
        API.ADMIN_IMPORT_GEDCOM,
        files={"file": ("import.ged", minimal_gedcom.encode("utf-8"), "application/octet-stream")},
        timeout=TIMEOUTS.api_long,
    )
    assert r.status_code in (200, 201, 202), (
        f"GEDCOM import not accessible to auth_v2 owner: "
        f"{r.status_code} {r.text[:200]}"
    )
