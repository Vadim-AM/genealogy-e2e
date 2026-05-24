"""POM for the signup overflow waitlist modal.

Selectors verified against signup.html:
- #waitlistOverlay (.is-open when visible)
- #waitlistTitle — heading text
- #waitlistBody2 — message body with email + waitlist info
- #waitlistOk — «Понятно» close button
"""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import ErrMsg

_IS_OPEN = re.compile(r"\bis-open\b")


class WaitlistModal:
    """Drives the signup-overflow waitlist modal."""

    def __init__(self, page: Page):
        self.page = page
        self.overlay = page.locator("#waitlistOverlay")  # no semantic: custom widget, no ARIA
        self.title = page.locator("#waitlistTitle")  # no semantic: custom widget, no ARIA
        self.body = page.locator("#waitlistBody2")  # no semantic: dynamic content, no ARIA
        self.btn_ok = page.locator("#waitlistOk")  # no semantic: custom widget, no ARIA

    def expect_open(self) -> None:
        """Assert the waitlist overlay has the is-open class."""
        with step("проверка: модалка waitlist открыта"):
            expect(self.overlay, ErrMsg.wrong_css_class).to_have_class(_IS_OPEN)

    def expect_closed(self) -> None:
        """Assert the waitlist overlay does not have the is-open class."""
        with step("проверка: модалка waitlist закрыта"):
            expect(self.overlay, ErrMsg.overlay_should_be_closed).not_to_have_class(_IS_OPEN)

    def click_ok(self) -> None:
        """Click the 'Понятно' button to dismiss the modal."""
        with step("клик «Понятно» в модалке waitlist"):
            self.btn_ok.click()

    def dismiss_via_escape(self) -> None:
        """Press Escape to close the modal."""
        with step("нажатие Esc для закрытия модалки waitlist"):
            self.page.keyboard.press("Escape")

    def fallback_link(self) -> Locator:
        """Return the /wait fallback link locator inside the body."""
        return self.body.locator('a[href*="/wait"]')
