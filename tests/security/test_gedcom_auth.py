"""INV-GEDCOM-001: GEDCOM endpoints not migrated to auth_v2.

Was xfail until upstream commit `17d11b1` ("fix(auth): bridge auth_v2
owner для photos и GEDCOM"). Now plain regression — auth_v2 owner
может export/import без legacy admin password.
"""

from __future__ import annotations

from tests.api_paths import API
from tests.response import expect_response
from tests.timeouts import TIMEOUTS


def test_owner_can_export_gedcom_via_auth_v2(owner_user, tenant_client):
    """INV-GEDCOM-001 (export): auth_v2 owner получает 200 + GEDCOM body."""
    api = tenant_client(owner_user)
    r = api.get(API.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)
    expect_response(r, label="GEDCOM export auth_v2").status(200)
    # GEDCOM-формат начинается с '0 HEAD'. Response charset=utf-8
    # (см. test_owner_ui::test_owner_export_gedcom_returns_valid_dump),
    # так что r.text — корректно декодированная строка.
    assert "0 HEAD" in r.text[:200], (
        f"response is not a GEDCOM file: starts with {r.text[:80]!r}"
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
    expect_response(r, label="GEDCOM import auth_v2").status(200)
