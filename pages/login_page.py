"""POM for /login.

Locale-aware: button name comes from `tests.messages`. When the product
adds `data-testid` to the submit button, swap to that.
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Buttons, t

from .base import BasePage


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def email(self) -> Locator:
        """no semantic: login form has no <label>"""
        return self.page.locator('input[name="email"]')

    @property
    def password(self) -> Locator:
        """no semantic: login form has no <label>"""
        return self.page.locator('input[name="password"]')

    @property
    def submit_btn(self) -> Locator:
        """Login submit button."""
        return self.page.get_by_role("button", name=t(Buttons.LOGIN))

    @property
    def error_msg(self) -> Locator:
        """Login error / status text container."""
        return self.page.get_by_role("status")

    @property
    def form(self) -> Locator:
        """no semantic: form element by ID"""
        return self.page.locator("#loginForm")

    def login(self, email: str, password: str) -> Self:
        """Fill credentials and click the login button."""
        with step("действие: вход в систему"):
            self.email.fill(email)
            self.password.fill(password)
            self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        """Assert email, password and submit button are visible."""
        with step("проверка: форма входа видима"):
            expect(self.email).to_be_visible()
            expect(self.password).to_be_visible()
            expect(self.submit_btn).to_be_visible()

    def expect_error(self) -> None:
        """Assert the status message contains a non-empty error text."""
        with step("проверка: ошибка входа"):
            expect(self.error_msg).not_to_have_text("")
