"""POM for /owner — tenant owner dashboard."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from .base import BasePage


class OwnerPage(BasePage):
    URL = "/owner"

    TABS = ["settings", "invites", "export", "subscription", "danger"]

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Tabs ──────────────────────────────────────────────────────────

    @property
    def tab_settings(self) -> Locator:
        """no semantic: programmatic tab switching"""
        return self.page.locator('[data-tab="settings"]')

    @property
    def tab_invites(self) -> Locator:
        """no semantic: programmatic tab switching"""
        return self.page.locator('[data-tab="invites"]')

    @property
    def tab_export(self) -> Locator:
        """no semantic: programmatic tab switching"""
        return self.page.locator('[data-tab="export"]')

    @property
    def tab_subscription(self) -> Locator:
        """no semantic: programmatic tab switching"""
        return self.page.locator('[data-tab="subscription"]')

    @property
    def tab_danger(self) -> Locator:
        """no semantic: programmatic tab switching"""
        return self.page.locator('[data-tab="danger"]')

    # ── Settings tab inputs ───────────────────────────────────────────

    @property
    def cfg_site_name(self) -> Locator:
        """no semantic: <label> is sibling, not wrapper"""
        return self.page.locator("#cfg_site_name")

    @property
    def cfg_family_name(self) -> Locator:
        """no semantic: <label> is sibling"""
        return self.page.locator("#cfg_family_name")

    @property
    def cfg_regions(self) -> Locator:
        """no semantic: <label> is sibling"""
        return self.page.locator("#cfg_regions")

    @property
    def cfg_contact_email(self) -> Locator:
        """no semantic: <label> is sibling"""
        return self.page.locator("#cfg_contact_email")

    @property
    def cfg_about_text(self) -> Locator:
        """no semantic: <label> is sibling"""
        return self.page.locator("#cfg_about_text")

    @property
    def cfg_save(self) -> Locator:
        """no semantic: button text may change"""
        return self.page.locator("#cfgSave")

    # ── GEDCOM Import widget ─────────────────────────────────────────

    @property
    def import_root(self) -> Locator:
        """no semantic: import widget container"""
        return self.page.locator("#gedcomImportRoot")

    @property
    def import_file_input(self) -> Locator:
        """no semantic: file input within import widget"""
        return self.import_root.locator("#gedcomImportFile")

    @property
    def import_upload_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-upload"]')

    @property
    def import_confirm_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-confirm"]')

    @property
    def import_cancel_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-cancel"]')

    @property
    def import_retry_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-retry"]')

    @property
    def import_again_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-import-again"]')

    @property
    def import_open_tree_btn(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.import_root.locator('[data-action="gedcom-open-tree"]')

    @property
    def import_stats(self) -> Locator:
        """no semantic: stats display, no ARIA"""
        return self.import_root.locator("[data-gedcom-stats]")

    @property
    def import_encoding_badge(self) -> Locator:
        """no semantic: encoding badge, no ARIA"""
        return self.import_root.locator("[data-gedcom-encoding]")

    @property
    def import_summary(self) -> Locator:
        """no semantic: summary display, no ARIA"""
        return self.import_root.locator("[data-gedcom-summary]")

    @property
    def import_error(self) -> Locator:
        """no semantic: error display, no ARIA"""
        return self.import_root.locator("[data-gedcom-error]")

    # ── Confirm dialog (lives on body, not inside import_root) ────────

    @property
    def confirm_dialog(self) -> Locator:
        """no semantic: dialog backdrop, no ARIA"""
        return self.page.locator('[data-testid="confirm-dialog-backdrop"]')

    @property
    def confirm_dialog_confirm(self) -> Locator:
        """no semantic: confirm action button"""
        return self.confirm_dialog.locator('[data-act="confirm"]')

    @property
    def confirm_dialog_cancel(self) -> Locator:
        """no semantic: cancel action button"""
        return self.confirm_dialog.locator('[data-act="cancel"]')

    @property
    def confirm_dialog_ok(self) -> Locator:
        """no semantic: alertDialog ok button"""
        return self.confirm_dialog.locator('[data-act="ok"]')

    # ── Methods ───────────────────────────────────────────────────────

    def tab_locator(self, name: str) -> Locator:
        """Return a tab locator by data-tab name."""
        return self.page.locator(f'[data-tab="{name}"]')

    def open_tab(self, name: str) -> Self:
        """Click a tab by its data-tab name."""
        self.tab_locator(name).click()
        return self

    def update_settings(self, *, site_name: str | None = None) -> Self:
        """Open the settings tab, optionally set site name, and save."""
        self.open_tab("settings")
        if site_name is not None:
            # The settings tab populates #cfg_site_name asynchronously
            # via GET /api/site/config (owner.js: `await r.json()`). The
            # field ships empty (placeholder only), so wait for populate
            # to fill it before fill() — otherwise the populate response
            # lands after fill() and overwrites it, and save() submits
            # the stale default.
            expect(self.cfg_site_name).not_to_have_value("")
            self.cfg_site_name.fill(site_name)
        self.cfg_save.click()
        return self

    def soft_check_all_tabs(self, soft) -> None:
        """Soft-assert all owner dashboard tabs are visible."""
        for tab in self.TABS:
            soft(self.tab_locator(tab)).to_be_visible()

    # ──────────────────────────────────────────────────────────────────
    # GEDCOM Import widget helpers
    # ──────────────────────────────────────────────────────────────────

    def expect_import_state(self, state: str) -> None:
        """Assert import widget is in given state (IDLE, FILE_PICKED,
        UPLOADING, PREVIEW, CONFIRMING, DONE, ERROR)."""
        expect(self.import_root).to_have_attribute("data-gedcom-state", state)

    def upload_ged(self, *, filename: str, content: bytes) -> None:
        """Set the file input via in-memory buffer, then click Upload."""
        self.import_file_input.set_input_files(
            files=[  # type: ignore[arg-type]
                {
                    "name": filename,
                    "mimeType": "application/octet-stream",
                    "buffer": content,
                }
            ]
        )
        self.import_upload_btn.click()

    def confirm_import_via_dialog(self) -> None:
        """Click widget's Confirm -> confirmDialog appears -> click Confirm.

        Two-stage gate by design: widget triggers confirmDialog before
        writing to DB.
        """
        self.import_confirm_btn.click()
        self.confirm_dialog_confirm.click()

    def set_file_raw(self, *, name: str, mime: str, buffer: bytes) -> None:
        """Set the file input directly (bypassing upload_ged's Upload click).

        Used for client-side validation tests (wrong extension, empty file,
        oversize) where the widget rejects before any POST.
        """
        self.import_file_input.set_input_files(
            files=[{"name": name, "mimeType": mime, "buffer": buffer}]  # type: ignore[arg-type]
        )
