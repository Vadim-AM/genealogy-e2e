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

import httpx

from tests.timeouts import TIMEOUTS
from playwright.sync_api import Page, expect

from tests.messages import TestData
from tests.pages.owner_page import OwnerPage


def test_owner_settings_tab_has_inputs(owner_page: Page):
    """F-OU-2: settings tab has site_name input and save button."""
    owner = OwnerPage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")
    owner.open_tab("settings")
    expect(owner.cfg_site_name).to_be_visible()
    expect(owner.cfg_save).to_be_visible()


def test_owner_settings_save_persists(owner_page: Page, owner_user, base_url: str):
    """F-OU-2: save site_name → backend reflects the new value via /api/site/config.

    Was xfail under BUG-MT-001 — current HEAD passes, marker dropped on 28.04.
    """
    owner = OwnerPage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")

    new_name = TestData.SAMPLE_SITE_NAME
    with owner_page.expect_response("**/api/site/config") as resp_info:
        owner.update_settings(site_name=new_name)
    assert resp_info.value.ok, \
        f"PATCH /api/site/config returned {resp_info.value.status}"

    r = httpx.get(
        f"{base_url}/api/site/config",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["site_name"] == new_name, \
        f"site_name not persisted (BUG-MT-001 likely): got {r.json().get('site_name')!r}"


def test_owner_export_gedcom_returns_valid_dump(owner_user, base_url: str):
    """F-OU-4: GEDCOM export returns a 5.5.1-shaped text dump."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tenant/export?format=gedcom",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    r.raise_for_status()
    assert r.text.lstrip().startswith(TestData.GEDCOM_HEAD), \
        f"GEDCOM export missing prologue: {r.text[:200]!r}"


def test_owner_export_zip_contains_manifest_and_people(owner_user, base_url: str):
    """F-OU-4: ZIP export contains people.json + MANIFEST.txt."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tenant/export?format=zip",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    r.raise_for_status()
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "people.json" in names, f"people.json missing: {names}"
        assert "MANIFEST.txt" in names, f"MANIFEST.txt missing: {names}"
