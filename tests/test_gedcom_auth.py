"""INV-GEDCOM-001: GEDCOM endpoints not migrated to auth_v2.

Repatriation use-case (Roman Mnev и др.) — основной flow:
1. Owner экспортирует GEDCOM из своего tenant (Pro tier feature).
2. Импортирует в архивную систему.

Run security 28.04 night выявил: `/api/admin/export-gedcom` и
`/api/admin/import-gedcom` всё ещё гейтированы через `require_admin`
(legacy admin password gate), не через `require_owner` / auth_v2
session. Owner с auth_v2 cookie получает 401.

Симптом для пользователя: купил Researcher/Pro, идёт в
Кабинет → Экспорт → клик «Скачать GEDCOM» → 401 в console, файл
не скачивается. Pro tier обещание «expert export» не выполняется.

Same architectural fix как INV-PHOTO-001a — два legacy endpoint
кластера осталось мигрировать (admin upload-photo и admin gedcom).
"""

from __future__ import annotations

import httpx
import pytest

from tests.timeouts import TIMEOUTS


@pytest.mark.xfail(
    reason="INV-GEDCOM-001: /api/admin/export-gedcom гейтирован "
           "require_admin (legacy admin password). Owner с auth_v2 "
           "cookie → 401 (Run security 28.04 night). Repatriation "
           "use-case недоступен для всех multi-tenant клиентов. Fix: "
           "перенести handler на auth_v2 require_owner или сделать "
           "новый /api/account/tenant/export-gedcom endpoint.",
    strict=False,
)
def test_owner_can_export_gedcom_via_auth_v2(owner_user, base_url: str):
    """INV-GEDCOM-001 (export side): auth_v2 owner получает 200 +
    GEDCOM body, не 401."""
    r = httpx.get(
        f"{base_url}/api/admin/export-gedcom",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_long,
    )
    assert r.status_code == 200, (
        f"GEDCOM export not accessible to auth_v2 owner: "
        f"{r.status_code} {r.text[:200]}"
    )
    # GEDCOM-формат начинается с '0 HEAD'.
    assert b"0 HEAD" in r.content[:200] or "0 HEAD" in r.text[:200], (
        f"response is not a GEDCOM file: starts with {r.content[:80]!r}"
    )


@pytest.mark.xfail(
    reason="INV-GEDCOM-001 (import side): /api/admin/import-gedcom "
           "тот же legacy admin gate. Multi-tenant owner не может "
           "импортировать. См. export side выше.",
    strict=False,
)
def test_owner_can_import_gedcom_via_auth_v2(owner_user, base_url: str):
    """INV-GEDCOM-001 (import side): auth_v2 owner может POST GEDCOM
    (response 200/202), не 401."""
    minimal_gedcom = (
        "0 HEAD\n"
        "1 SOUR Genealogy-e2e\n"
        "0 @I1@ INDI\n"
        "1 NAME Тестовый /Импорт/\n"
        "0 TRLR\n"
    )
    r = httpx.post(
        f"{base_url}/api/admin/import-gedcom",
        files={"file": ("import.ged", minimal_gedcom.encode("utf-8"), "application/octet-stream")},
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_long,
    )
    assert r.status_code in (200, 201, 202), (
        f"GEDCOM import not accessible to auth_v2 owner: "
        f"{r.status_code} {r.text[:200]}"
    )
