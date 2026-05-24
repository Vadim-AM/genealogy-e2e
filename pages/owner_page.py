"""POM for /owner — tenant owner dashboard."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from .base import BasePage


class OwnerPage(BasePage):
    URL = "/owner"

    TABS = ["settings", "invites", "export", "subscription", "danger"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.tab_settings = page.locator('[data-tab="settings"]')  # no semantic: programmatic tab switching
        self.tab_invites = page.locator('[data-tab="invites"]')  # no semantic: programmatic tab switching
        self.tab_export = page.locator('[data-tab="export"]')  # no semantic: programmatic tab switching
        self.tab_subscription = page.locator('[data-tab="subscription"]')  # no semantic: programmatic tab switching
        self.tab_danger = page.locator('[data-tab="danger"]')  # no semantic: programmatic tab switching

        # Settings tab inputs — labels are siblings without for=, get_by_label doesn't match.
        self.cfg_site_name = page.locator("#cfg_site_name")  # no semantic: <label> is sibling, not wrapper
        self.cfg_family_name = page.locator("#cfg_family_name")  # no semantic: <label> is sibling
        self.cfg_regions = page.locator("#cfg_regions")  # no semantic: <label> is sibling
        self.cfg_contact_email = page.locator("#cfg_contact_email")  # no semantic: <label> is sibling
        self.cfg_about_text = page.locator("#cfg_about_text")  # no semantic: <label> is sibling
        self.cfg_save = page.locator("#cfgSave")  # no semantic: button text may change

        # Invite tab locators omitted — invite flow is exercised via API
        # fixtures (create_invite / accept_invite in _fixtures/users.py).
        # UI locators to be added when product exposes `data-invite-url`.

        # GEDCOM Import widget (Фаза 2). Стабильные хуки —
        # data-action и data-gedcom-* атрибуты, не текстовые селекторы.
        self.import_root = page.locator("#gedcomImportRoot")
        self.import_file_input = self.import_root.locator("#gedcomImportFile")
        self.import_upload_btn = self.import_root.locator('[data-action="gedcom-upload"]')
        self.import_confirm_btn = self.import_root.locator('[data-action="gedcom-confirm"]')
        self.import_cancel_btn = self.import_root.locator('[data-action="gedcom-cancel"]')
        self.import_retry_btn = self.import_root.locator('[data-action="gedcom-retry"]')
        self.import_again_btn = self.import_root.locator('[data-action="gedcom-import-again"]')
        self.import_open_tree_btn = self.import_root.locator(
            '[data-action="gedcom-open-tree"]'
        )
        self.import_stats = self.import_root.locator("[data-gedcom-stats]")
        self.import_encoding_badge = self.import_root.locator("[data-gedcom-encoding]")
        self.import_summary = self.import_root.locator("[data-gedcom-summary]")
        self.import_error = self.import_root.locator("[data-gedcom-error]")
        # confirmDialog overlay live на body — не внутри import_root
        self.confirm_dialog = page.locator('[data-testid="confirm-dialog-backdrop"]')
        self.confirm_dialog_confirm = self.confirm_dialog.locator('[data-act="confirm"]')
        self.confirm_dialog_cancel = self.confirm_dialog.locator('[data-act="cancel"]')
        self.confirm_dialog_ok = self.confirm_dialog.locator('[data-act="ok"]')  # alertDialog

    def open_tab(self, name: str) -> Self:
        """Click a tab by its data-tab name."""
        self.page.locator(f'[data-tab="{name}"]').click()
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
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()

    # ──────────────────────────────────────────────────────────────────
    # GEDCOM Import widget helpers (Фаза 2)
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
        """Click widget's Confirm → confirmDialog appears → click Импортировать.

        Two-stage gate by design (Фаза 2): widget triggers confirmDialog
        перед записью в БД.
        """
        self.import_confirm_btn.click()
        self.confirm_dialog_confirm.click()
