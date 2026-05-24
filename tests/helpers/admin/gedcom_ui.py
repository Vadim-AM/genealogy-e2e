"""GEDCOM import UI helpers."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.pages.owner_page import OwnerPage
from tests.step import step


def import_via_ui(owner_page: Page, ged_content: str, filename: str) -> None:
    """User flow: open /owner -> Import tab -> upload -> confirm -> DONE."""
    with step(f"import GEDCOM {filename!r} via UI"):
        owner = OwnerPage(owner_page)
        owner_page.goto("/owner")
        owner_page.wait_for_load_state("networkidle")
        owner.open_tab("export")
        expect(owner.import_root).to_have_attribute("data-gedcom-state", "IDLE")

        owner.upload_ged(filename=filename, content=ged_content.encode("utf-8"))
        owner.expect_import_state("PREVIEW")
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")


def open_import_tab(owner_page: Page) -> OwnerPage:
    """Navigate to /owner and open the GEDCOM import tab."""
    owner = OwnerPage(owner_page)
    owner_page.goto("/owner")
    # `networkidle` нужен здесь специально: GEDCOM widget mount'ится async
    # через JS после loadMe() fetch -- `domcontentloaded` слишком ранний,
    # widget element в DOM ещё нет.
    owner_page.wait_for_load_state("networkidle")
    owner.open_tab("export")
    # Widget mounts after loadMe() resolves -- wait for IDLE state
    expect(owner.import_root).to_have_attribute("data-gedcom-state", "IDLE")
    return owner
