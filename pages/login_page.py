"""POM for /login.

Locale-aware: button name comes from `tests.messages`. When the product
adds `data-testid` to the submit button, swap to that.
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from src.texts import Buttons, t

from .base import BasePage


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator('input[name="email"]')  # no semantic: login form has no <label>
        self.password = page.locator('input[name="password"]')  # no semantic: login form has no <label>
        self.submit_btn = page.get_by_role("button", name=t(Buttons.LOGIN))
        # Login error / status text container — main.py:602 renders it as
        # `<div id="msg" role="status" aria-live="polite"></div>`. JS sets
        # textContent on failure (no class change for error vs success — text
        # presence is the signal).
        self.error_msg = page.get_by_role("status")

    def login(self, email: str, password: str) -> Self:
        """Fill credentials and click the login button."""
        self.email.fill(email)
        self.password.fill(password)
        self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        """Assert email, password and submit button are visible."""
        expect(self.email).to_be_visible()
        expect(self.password).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def expect_error(self) -> None:
        """Assert the status message contains a non-empty error text."""
        # Error visible = #msg has non-empty text content.
        expect(self.error_msg).not_to_have_text("")
