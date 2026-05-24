"""POM for /wait — waitlist signup landing."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from src.texts import Buttons, Labels, t

from .base import BasePage


class WaitPage(BasePage):
    URL = "/wait"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.get_by_label(t(Labels.WAITLIST_EMAIL))
        self.submit_btn = page.get_by_role("button", name=t(Buttons.WAITLIST_SUBMIT))
        self.result = page.locator("#result")  # no semantic: generic result div
        self.form = page.locator("#waitForm")  # no semantic: form container

    def submit_email(self, email: str) -> Self:
        """Fill the email and click submit to join the waitlist."""
        self.email.fill(email)
        self.submit_btn.click()
        return self

    def expect_success(self) -> None:
        """`#result` becomes visible with non-empty content. Auto-wait via
        Playwright default — no explicit timeout needed."""
        expect(self.result).to_be_visible()
        expect(self.result).not_to_have_text("")

    def expect_visible_form(self) -> None:
        """Assert the waitlist form elements are visible."""
        expect(self.form).to_be_visible()
        expect(self.email).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def is_email_valid(self) -> bool:
        """Return the HTML5 validity state of the email input."""
        return self.page.evaluate("() => document.getElementById('email').checkValidity()")

    def page_content(self) -> str:
        """Return the full HTML content of the page."""
        return self.page.content()
