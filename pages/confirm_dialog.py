"""POM for the custom confirm-dialog modal.

Selectors from js/components/confirm-dialog.js. The dialog is a custom
modal (not a native browser confirm()) triggered by confirmDialog() calls
throughout the product — most commonly delete-person flows.

Layout:
    .confirm-dialog-backdrop   <- overlay, click = cancel
    .confirm-dialog            <- modal panel
      (text content)           <- message with action details
      button (Cancel)          <- role=button, name from Buttons.CANCEL
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Buttons, t


class ConfirmDialog:
    """Drives the custom confirm-dialog: inspect text, confirm, cancel."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def container(self) -> Locator:
        """Confirm dialog panel."""
        return self.page.locator('[data-testid="confirm-dialog"]').first

    @property
    def backdrop(self) -> Locator:
        """Confirm dialog backdrop overlay."""
        return self.page.locator('[data-testid="confirm-dialog-backdrop"]').first

    def expect_visible(self) -> None:
        """Assert the confirm dialog is visible."""
        with step("проверка: диалог виден"):
            expect(self.container).to_be_visible()

    def text(self) -> str:
        """Return the text content of the dialog."""
        return self.container.inner_text()

    def confirm(self) -> None:
        """Press Enter to confirm (confirm-dialog.js: Enter -> cleanup(true))."""
        with step("действие: подтвердить"):
            self.page.keyboard.press("Enter")

    @property
    def cancel_btn(self) -> Locator:
        """Кнопка «Отмена» в диалоге."""
        return self.container.get_by_role("button", name=t(Buttons.CANCEL))

    def cancel(self) -> None:
        """Click the Cancel button inside the dialog."""
        with step("действие: отменить"):
            self.cancel_btn.click()

    def cancel_and_settle(self) -> None:
        """Click Cancel and wait for the DOM to settle after dialog closes."""
        with step("действие: отменить и дождаться закрытия"):
            self.cancel()
            self.page.wait_for_load_state("domcontentloaded")

    def dismiss_via_escape(self) -> None:
        """Press Escape to dismiss (confirm-dialog.js: Escape -> cleanup(false))."""
        with step("действие: закрыть по Escape"):
            self.page.keyboard.press("Escape")

    def dismiss_via_backdrop(self) -> None:
        """Click the backdrop overlay to dismiss."""
        with step("действие: закрыть по backdrop"):
            expect(self.backdrop).to_be_visible()
            self.backdrop.click(position={"x": 5, "y": 5})

    def expect_hidden(self) -> None:
        """Assert the confirm dialog is no longer visible."""
        with step("проверка: диалог скрыт"):
            expect(self.container).not_to_be_visible()

    def dialog_button(self, name: str) -> Locator:
        """Return a button inside the dialog by accessible name."""
        return self.container.get_by_role("button", name=name)

    def click_button(self, name: str) -> None:
        """Click a button inside the dialog by its accessible name."""
        self.dialog_button(name).click()
