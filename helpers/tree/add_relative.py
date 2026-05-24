"""Add-relative modal helpers."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from pages.add_relative_modal import AddRelativeModal
from pages.profile_panel import ProfilePanel
from src.texts import ErrMsg


def add_sibling_without_auto_parents(
    page: Page,
    *,
    surname: str,
    given: str,
    birth: str = "",
    gender: str | None = None,
) -> AddRelativeModal:
    """Open add-sibling modal, uncheck auto-parent, fill, save, and wait for close."""
    panel = ProfilePanel(page)
    panel.click_add_sibling()

    modal = AddRelativeModal(page)
    modal.expect_visible()
    # Native `#addRelSiblingShareParents` обёрнут `<label class="checkbox">`
    # и visually-hidden; POM helper кликает по label (см. AddRelativeModal).
    modal.uncheck_share_parents()

    modal.fill_fio(surname=surname, given=given, birth=birth)
    if gender:
        modal.select_gender(gender)

    with page.expect_response(f"**{routes.PEOPLE}**") as resp:
        modal.save()
    should.be_true(resp.value.ok, ErrMsg.editor_save_failed)
    expect(modal.overlay).not_to_be_visible()
    return modal
