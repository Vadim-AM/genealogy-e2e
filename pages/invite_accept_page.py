"""POM for /invite-accept?token=..."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Invite, t

from .base import BasePage


class InviteAcceptPage(BasePage):
    URL = "/invite-accept"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def title_el(self) -> Locator:
        """Invite accept heading."""
        return self.page.get_by_role("heading", level=2)

    @property
    def message(self) -> Locator:
        """Status message element."""
        return self.page.get_by_role("status")

    @property
    def link(self) -> Locator:
        """no semantic: dynamically populated href"""
        return self.page.locator("#link")

    @property
    def login_link(self) -> Locator:
        """Return the login link inside the invite message."""
        return self.page.get_by_role("link", name=t(Invite.LOGIN_LINK), exact=False).first

    @property
    def signup_link(self) -> Locator:
        """Return the signup link inside the invite message."""
        return self.page.get_by_role("link", name=t(Invite.SIGNUP_LINK), exact=False).first

    def open_with_token(self, token: str) -> Self:
        """Navigate to the invite-accept page with the given token."""
        with step("навигация: открыть приглашение по токену"):
            self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_message_loaded(self) -> None:
        """Assert the status message is visible."""
        with step("проверка: текст приглашения загружен"):
            expect(self.message).to_be_visible()

    def get_link_href(self) -> str:
        """Return the href attribute of the #link element."""
        return self.link.get_attribute("href") or ""

    def click_open_tree(self) -> None:
        """Click the open-tree link to navigate to the tenant tree."""
        with step("действие: кликнуть Открыть дерево"):
            self.link.click()

    def get_login_href(self) -> str:
        """Return the href attribute of the login link."""
        return self.login_link.get_attribute("href") or ""

    def get_signup_href(self) -> str:
        """Return the href attribute of the signup link."""
        return self.signup_link.get_attribute("href") or ""
