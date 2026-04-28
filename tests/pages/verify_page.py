"""POM for /verify?token=..."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class VerifyPage(BasePage):
    URL = "/verify"

    def __init__(self, page: Page):
        super().__init__(page)
        self.next_link = page.locator("#link")

    def open_with_token(self, token: str) -> "VerifyPage":
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_success(self) -> None:
        """After verification the success layout shows a "next step" link
        (`#link`) populated with the tenant slug. Visibility = success path."""
        expect(self.next_link).to_be_visible()
