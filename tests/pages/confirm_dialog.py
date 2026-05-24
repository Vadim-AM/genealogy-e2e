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

from playwright.sync_api import Page, expect

from tests.messages import Buttons, t


class ConfirmDialog:
    """Drives the custom confirm-dialog: inspect text, confirm, cancel."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator('[data-testid="confirm-dialog"]').first
        self.backdrop = page.locator('[data-testid="confirm-dialog-backdrop"]').first

    def expect_visible(self) -> None:
        """Assert the confirm dialog is visible."""
        expect(self.container).to_be_visible()

    def text(self) -> str:
        """Return the text content of the dialog."""
        return self.container.inner_text()

    def confirm(self) -> None:
        """Press Enter to confirm (confirm-dialog.js: Enter -> cleanup(true))."""
        self.page.keyboard.press("Enter")

    def cancel(self) -> None:
        """Click the Cancel button inside the dialog."""
        self.container.get_by_role("button", name=t(Buttons.CANCEL)).click()

    def dismiss_via_escape(self) -> None:
        """Press Escape to dismiss (confirm-dialog.js: Escape -> cleanup(false))."""
        self.page.keyboard.press("Escape")

    def dismiss_via_backdrop(self) -> None:
        """Click the backdrop overlay to dismiss."""
        expect(self.backdrop).to_be_visible()
        self.backdrop.click(position={"x": 5, "y": 5})

    def expect_hidden(self) -> None:
        """Assert the confirm dialog is no longer visible."""
        expect(self.container).not_to_be_visible()
