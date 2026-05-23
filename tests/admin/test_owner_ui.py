"""Owner UI (/owner) — F-OU-1..6: settings, invites, export, subscription, danger.

Owner is the tenant's primary admin. UI is rendered HTML with vanilla JS.

`test_owner_page_loads` removed — only asserted `<body>` visibility.
`test_owner_invites_tab_can_create_link` removed — fell back to API check
when UI did not produce the link, turning a UI test into an API test.
Reinstate in Wave 2 with concrete selectors for the invite-URL surface.
"""

from __future__ import annotations

import io
import zipfile

import allure
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.owner_page import OwnerPage
from tests.response import expect_response
from tests.timeouts import TIMEOUTS


@allure.title("Админка владельца: вкладка настроек содержит поля ввода")
def test_owner_settings_tab_has_inputs(owner_page: Page):
    """F-OU-2: settings tab has site_name input and save button."""
    owner = OwnerPage(owner_page).goto()
    owner_page.wait_for_load_state("domcontentloaded")
    owner.open_tab("settings")
    expect(owner.cfg_site_name).to_be_visible()
    expect(owner.cfg_save).to_be_visible()


@allure.title("Админка владельца: сохранение site_name попадает в бэкенд")
def test_owner_settings_save_persists(owner_page: Page, owner_user, tenant_client):
    """F-OU-2: save site_name → backend reflects the new value via /api/site/config.

    Awaits the WRITE specifically — a non-GET /api/site/config response,
    not the form-populate GET. `OwnerPage.update_settings()` itself waits
    for the populate GET to land before filling the field, so save()
    submits the typed value rather than the stale default.
    """
    owner = OwnerPage(owner_page).goto()
    owner_page.wait_for_load_state("domcontentloaded")

    new_name = TestData.SAMPLE_SITE_NAME
    with owner_page.expect_response(
        lambda r: r.url.endswith(API.SITE_CONFIG)
        and r.request.method != "GET"
    ) as resp_info:
        owner.update_settings(site_name=new_name)
    assert resp_info.value.ok, \
        f"save /api/site/config returned {resp_info.value.status}"

    api = tenant_client(owner_user)
    r = api.get(API.SITE_CONFIG)
    expect_response(r, label="GET site/config").status_ok().json_eq("site_name", new_name)


@allure.title("Экспорт: GEDCOM содержит заголовок 5.5.1 и SOUR проекта")
def test_owner_export_gedcom_returns_valid_dump(owner_user, tenant_client):
    """F-OU-4 / TC-EXPORT-1: GEDCOM export returns a 5.5.1-shaped text dump
    with attachment Content-Disposition and the canonical SOUR identifier."""
    api = tenant_client(owner_user)
    r = api.get(API.TENANT_EXPORT, params={"format": "gedcom"}, timeout=TIMEOUTS.api_long)
    expect_response(r, label="GEDCOM export").status_ok()

    # Header contract per docs/test-plan.md TC-EXPORT-1.
    ct = r.headers.get("content-type", "")
    assert ct.startswith("text/plain"), f"GEDCOM content-type: {ct!r}"
    assert "charset=utf-8" in ct.lower(), f"GEDCOM charset must be utf-8: {ct!r}"
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower(), \
        f"GEDCOM must download as attachment, got: {cd!r}"
    assert ".ged" in cd.lower(), f"GEDCOM filename must end in .ged, got: {cd!r}"

    # Body: GEDCOM 5.5.1 prologue with the project SOUR identifier.
    head = r.text.lstrip().splitlines()[:2]
    assert head[0] == TestData.GEDCOM_HEAD, \
        f"GEDCOM line 0 must be {TestData.GEDCOM_HEAD!r}, got {head[0]!r}"
    assert head[1].startswith("1 SOUR NashaRodoslovnaya"), \
        f"GEDCOM line 1 must identify the source app: {head[1]!r}"


@allure.title("Экспорт: ZIP содержит people.json и MANIFEST.txt")
def test_owner_export_zip_contains_manifest_and_people(owner_user, tenant_client):
    """F-OU-4 / TC-EXPORT-1: ZIP export carries application/zip with magic-bytes
    `50 4b 03 04` and includes people.json + MANIFEST.txt."""
    api = tenant_client(owner_user)
    r = api.get(API.TENANT_EXPORT, params={"format": "zip"}, timeout=TIMEOUTS.api_long)
    expect_response(r, label="ZIP export").status_ok()
    assert r.headers["content-type"] == "application/zip", \
        f"export must return ZIP: got {r.headers.get('content-type')!r}"
    # ZIP magic-bytes — first four bytes are PK\x03\x04 (50 4b 03 04).
    assert r.content[:4] == b"PK\x03\x04", \
        f"ZIP magic bytes mismatch: {r.content[:4]!r}"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "people.json" in names, f"people.json missing: {names}"
        assert "MANIFEST.txt" in names, f"MANIFEST.txt missing: {names}"
