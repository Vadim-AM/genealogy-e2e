"""POM for /invite-accept?token=..."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class InviteAcceptPage(BasePage):
    URL = "/invite-accept"

    def __init__(self, page: Page):
        super().__init__(page)
        self.title_el = page.locator("#title")
        self.message = page.locator("#msg")
        self.link = page.locator("#link")

    def open_with_token(self, token: str) -> "InviteAcceptPage":
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_message_loaded(self) -> None:
        expect(self.message).to_be_visible()
