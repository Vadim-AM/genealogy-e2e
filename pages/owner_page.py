"""POM for /owner — tenant owner dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from playwright.sync_api import Locator, Page, expect

if TYPE_CHECKING:
    from playwright.sync_api import Expect

from framework.step import step

from .base import BasePage


class OwnerPage(BasePage):
    URL = "/owner"

    TABS = ["settings", "invites", "export", "subscription", "danger"]

    def __init__(self, page: Page) -> None:
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

    # ── Onboarding demo controls ─────────────────────────────────────

    @property
    def clear_demo_btn(self) -> Locator:
        """no semantic: custom widget button, no ARIA"""
        return self.page.locator("#clearDemo")

    @property
    def keep_demo_btn(self) -> Locator:
        """no semantic: custom widget button, no ARIA"""
        return self.page.locator("#keepDemo")

    # ── Methods ───────────────────────────────────────────────────────

    def tab_locator(self, name: str) -> Locator:
        """Return a tab locator by data-tab name."""
        return self.page.locator(f'[data-tab="{name}"]')

    def open_tab(self, name: str) -> Self:
        """Click a tab by its data-tab name."""
        with step(f"действие: открыть вкладку {name!r}"):
            self.tab_locator(name).click()
        return self

    def update_settings(self, *, site_name: str | None = None) -> Self:
        """Open the settings tab, optionally set site name, and save."""
        with step("действие: обновить настройки"):
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

    def soft_check_all_tabs(self, soft: Expect) -> None:
        """Soft-assert all owner dashboard tabs are visible."""
        for tab in self.TABS:
            soft(self.tab_locator(tab)).to_be_visible()

    # ──────────────────────────────────────────────────────────────────
    # GEDCOM Import widget helpers
    # ──────────────────────────────────────────────────────────────────

    def expect_import_state(self, state: str) -> None:
        """Assert import widget is in given state (IDLE, FILE_PICKED,
        UPLOADING, PREVIEW, CONFIRMING, DONE, ERROR)."""
        with step(f"проверка: состояние импорта {state!r}"):
            expect(self.import_root).to_have_attribute("data-gedcom-state", state)

    def upload_ged(self, *, filename: str, content: bytes) -> None:
        """Set the file input via in-memory buffer, then click Upload."""
        with step(f"действие: загрузить GED файл {filename!r}"):
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
        with step("действие: подтвердить импорт"):
            self.import_confirm_btn.click()
            self.confirm_dialog_confirm.click()

    def set_file_raw(self, *, name: str, mime: str, buffer: bytes) -> None:
        """Set the file input directly (bypassing upload_ged's Upload click).

        Used for client-side validation tests (wrong extension, empty file,
        oversize) where the widget rejects before any POST.
        """
        with step(f"действие: установить файл {name!r}"):
            self.import_file_input.set_input_files(
                files=[{"name": name, "mimeType": mime, "buffer": buffer}]  # type: ignore[arg-type]
            )

    def import_gedcom_via_ui(self, ged_content: str, filename: str) -> None:
        """Full import flow: open export tab -> upload -> confirm -> DONE."""
        with step(f"действие: импорт GEDCOM {filename!r}"):
            self.goto()
            self.page.wait_for_load_state("domcontentloaded")
            self.open_tab("export")
            expect(self.import_root).to_have_attribute("data-gedcom-state", "IDLE")
            self.upload_ged(filename=filename, content=ged_content.encode("utf-8"))
            self.expect_import_state("PREVIEW")
            self.confirm_import_via_dialog()
            self.expect_import_state("DONE")

    def click_import_cancel(self) -> None:
        """Click the Cancel button on the import widget."""
        with step("действие: отменить импорт"):
            self.import_cancel_btn.click()

    def click_import_confirm(self) -> None:
        """Click the Confirm button on the import widget."""
        with step("действие: подтвердить импорт"):
            self.import_confirm_btn.click()

    def click_import_again(self) -> None:
        """Click the 'Import again' button after a completed import."""
        with step("действие: импортировать ещё"):
            self.import_again_btn.click()

    def click_import_retry(self) -> None:
        """Click the Retry button after an import error."""
        with step("действие: повторить импорт"):
            self.import_retry_btn.click()

    def click_confirm_dialog_ok(self) -> None:
        """Click the OK button in the confirm/alert dialog."""
        with step("действие: нажать ОК в диалоге"):
            self.confirm_dialog_ok.click()

    def click_confirm_dialog_cancel(self) -> None:
        """Click the Cancel button in the confirm dialog."""
        with step("действие: нажать Отмена в диалоге"):
            self.confirm_dialog_cancel.click()

    def goto_import_tab(self) -> Self:
        """Navigate to /owner and open the GEDCOM import tab."""
        with step("навигация: вкладка импорта"):
            self.goto()
            self.page.wait_for_load_state("domcontentloaded")
            self.open_tab("export")
            expect(self.import_root).to_have_attribute("data-gedcom-state", "IDLE")
        return self

    def click_clear_demo(self) -> None:
        """Click the 'clear demo data' control (opens confirm dialog)."""
        with step("действие: удалить демо-данные"):
            self.clear_demo_btn.click()

    def click_keep_demo(self) -> None:
        """Click the 'keep demo as template' control (opens confirm dialog)."""
        with step("действие: сохранить демо-данные как шаблон"):
            self.keep_demo_btn.click()
