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
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes, site_api
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from pages.owner_page import OwnerPage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Админка владельца: вкладка настроек содержит поля ввода")
def test_owner_settings_tab_has_inputs(owner_page: Page, pages: PageFactory):
    """F-OU-2: settings tab has site_name input and save button."""
    with step("действие: открытие вкладки настроек"):
        owner = pages.navigate_to(OwnerPage)
        owner_page.wait_for_load_state("domcontentloaded")
        owner.open_tab("settings")

    with step("проверка: поле site_name и кнопка сохранения видны"):
        expect(owner.cfg_site_name, ErrMsg.element_not_visible).to_be_visible()
        expect(owner.cfg_save, ErrMsg.button_not_visible).to_be_visible()


@allure.title("Админка владельца: сохранение site_name попадает в бэкенд")
def test_owner_settings_save_persists(owner_page: Page, owner_user, tenant_client, pages: PageFactory):
    """F-OU-2: save site_name → backend reflects the new value via /api/site/config.

    Awaits the WRITE specifically — a non-GET /api/site/config response,
    not the form-populate GET. `OwnerPage.update_settings()` itself waits
    for the populate GET to land before filling the field, so save()
    submits the typed value rather than the stale default.
    """
    with step("действие: сохранение нового site_name через UI"):
        owner = pages.navigate_to(OwnerPage)
        owner_page.wait_for_load_state("domcontentloaded")

        new_name = TestData.SAMPLE_SITE_NAME
        with owner_page.expect_response(
            lambda r: r.url.endswith(routes.SITE_CONFIG)
            and r.request.method != "GET"
        ) as resp_info:
            owner.update_settings(site_name=new_name)
        assert resp_info.value.ok, \
            f"save /api/site/config returned {resp_info.value.status}"

    with step("проверка: backend отдаёт новое значение"):
        api = tenant_client(owner_user)
        cfg = site_api.get_site_config(api)
        assert cfg.site_name == new_name, \
            f"site_name: expected {new_name!r}, got {cfg.site_name!r}"


@allure.title("Экспорт: GEDCOM содержит заголовок 5.5.1 и SOUR проекта")
def test_owner_export_gedcom_returns_valid_dump(owner_user, tenant_client):
    """F-OU-4 / TC-EXPORT-1: GEDCOM export returns a 5.5.1-shaped text dump
    with attachment Content-Disposition and the canonical SOUR identifier."""
    with step("действие: экспорт GEDCOM"):
        api = tenant_client(owner_user)
        r = api.get(routes.TENANT_EXPORT, params={"format": "gedcom"}, timeout=TIMEOUTS.api_long)
        expect_response(r, label="GEDCOM export").status_ok()

    with step("проверка: заголовки Content-Type и Content-Disposition"):
        ct = r.headers.get("content-type", "")
        assert ct.startswith("text/plain"), f"GEDCOM content-type: {ct!r}"
        assert "charset=utf-8" in ct.lower(), f"GEDCOM charset must be utf-8: {ct!r}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), \
            f"GEDCOM must download as attachment, got: {cd!r}"
        assert ".ged" in cd.lower(), f"GEDCOM filename must end in .ged, got: {cd!r}"

    with step("проверка: body содержит GEDCOM 5.5.1 header и SOUR"):
        head = r.text.lstrip().splitlines()[:2]
        assert head[0] == TestData.GEDCOM_HEAD, \
            f"GEDCOM line 0 must be {TestData.GEDCOM_HEAD!r}, got {head[0]!r}"
        assert head[1].startswith("1 SOUR NashaRodoslovnaya"), \
            f"GEDCOM line 1 must identify the source app: {head[1]!r}"


@allure.title("Экспорт: ZIP содержит people.json и MANIFEST.txt")
def test_owner_export_zip_contains_manifest_and_people(owner_user, tenant_client):
    """F-OU-4 / TC-EXPORT-1: ZIP export carries application/zip with magic-bytes
    `50 4b 03 04` and includes people.json + MANIFEST.txt."""
    with step("действие: экспорт ZIP"):
        api = tenant_client(owner_user)
        r = api.get(routes.TENANT_EXPORT, params={"format": "zip"}, timeout=TIMEOUTS.api_long)
        expect_response(r, label="ZIP export").status_ok()

    with step("проверка: ZIP содержит people.json и MANIFEST.txt"):
        assert r.headers["content-type"] == "application/zip", \
            f"export must return ZIP: got {r.headers.get('content-type')!r}"
        assert r.content[:4] == b"PK\x03\x04", \
            f"ZIP magic bytes mismatch: {r.content[:4]!r}"
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names = zf.namelist()
            assert "people.json" in names, f"people.json missing: {names}"
            assert "MANIFEST.txt" in names, f"MANIFEST.txt missing: {names}"
