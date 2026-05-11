"""POM for /owner — tenant owner dashboard."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from .base import BasePage


class OwnerPage(BasePage):
    URL = "/owner"

    TABS = ["settings", "invites", "export", "subscription", "danger"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.tab_settings = page.locator('[data-tab="settings"]')
        self.tab_invites = page.locator('[data-tab="invites"]')
        self.tab_export = page.locator('[data-tab="export"]')
        self.tab_subscription = page.locator('[data-tab="subscription"]')
        self.tab_danger = page.locator('[data-tab="danger"]')

        # Settings
        self.cfg_site_name = page.locator("#cfg_site_name")
        self.cfg_family_name = page.locator("#cfg_family_name")
        self.cfg_regions = page.locator("#cfg_regions")
        self.cfg_contact_email = page.locator("#cfg_contact_email")
        self.cfg_about_text = page.locator("#cfg_about_text")
        self.cfg_save = page.locator("#cfgSave")

        # Invites
        self.inv_email = page.locator("#invEmail")
        self.inv_role = page.locator("#invRole")
        self.inv_create = page.locator("#invCreate")
        self.inv_list = page.locator("#invList")

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
        self.confirm_dialog = page.locator(".confirm-dialog-backdrop")
        self.confirm_dialog_confirm = self.confirm_dialog.locator('[data-act="confirm"]')
        self.confirm_dialog_cancel = self.confirm_dialog.locator('[data-act="cancel"]')
        self.confirm_dialog_ok = self.confirm_dialog.locator('[data-act="ok"]')  # alertDialog

    def open_tab(self, name: str) -> "OwnerPage":
        self.page.locator(f'[data-tab="{name}"]').click()
        return self

    def update_settings(self, *, site_name: str | None = None) -> "OwnerPage":
        self.open_tab("settings")
        if site_name is not None:
            self.cfg_site_name.fill(site_name)
        self.cfg_save.click()
        return self

    def create_invite(self, *, email: str = "", role: str = "viewer") -> str | None:
        """Create a share invite. Returns the URL captured in the UI (or None)."""
        self.open_tab("invites")
        if email and self.inv_email.count():
            self.inv_email.fill(email)
        if self.inv_role.count():
            self.inv_role.select_option(role)
        self.inv_create.click()
        # Try to capture the produced URL — different markup supports a few
        # layouts: <a data-invite-url>, modal with .invite-url-text, etc.
        for sel in ("[data-invite-url]", ".invite-url-text", ".invite-url", "#inviteUrlBox a"):
            loc = self.page.locator(sel).first
            if loc.count() and loc.is_visible():
                href = loc.get_attribute("href") or loc.text_content()
                if href:
                    return href.strip()
        return None

    def soft_check_all_tabs(self, soft) -> None:
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
            files=[
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
