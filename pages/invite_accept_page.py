"""POM for /invite-accept?token=..."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from .base import BasePage


class InviteAcceptPage(BasePage):
    URL = "/invite-accept"

    def __init__(self, page: Page):
        super().__init__(page)
        self.title_el = page.get_by_role("heading", level=2)
        self.message = page.get_by_role("status")
        self.link = page.locator("#link")  # no semantic: dynamically populated href

    def open_with_token(self, token: str) -> Self:
        """Navigate to the invite-accept page with the given token."""
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_message_loaded(self) -> None:
        """Assert the status message is visible."""
        expect(self.message).to_be_visible()
