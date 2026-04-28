"""POM for /wait — waitlist signup landing."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class WaitPage(BasePage):
    URL = "/wait"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator("#email")
        self.submit_btn = page.locator("#submitBtn")
        self.result = page.locator("#result")
        self.form = page.locator("#waitForm")

    def submit_email(self, email: str) -> "WaitPage":
        self.email.fill(email)
        self.submit_btn.click()
        return self

    def expect_success(self) -> None:
        """`#result` becomes visible with non-empty content. Auto-wait via
        Playwright default — no explicit timeout needed."""
        expect(self.result).to_be_visible()
        expect(self.result).not_to_have_text("")

    def expect_visible_form(self) -> None:
        expect(self.form).to_be_visible()
        expect(self.email).to_be_visible()
        expect(self.submit_btn).to_be_visible()
