"""POM for /verify?token=..."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class VerifyPage(BasePage):
    URL = "/verify"

    def __init__(self, page: Page):
        super().__init__(page)

    def open_with_token(self, token: str) -> "VerifyPage":
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_success(self) -> None:
        # Multiple elements may contain the success copy (h2 + button); pick first.
        target = self.page.get_by_role("link", name="Перейти", exact=False).or_(
            self.page.locator("#link")
        ).first
        expect(target).to_be_visible(timeout=10_000)
