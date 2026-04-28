"""POM for /login."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator('input[name="email"]').first
        self.password = page.locator('input[name="password"]').first
        self.submit_btn = page.get_by_role("button", name="Войти", exact=False).first
        self.error_msg = page.locator(".error, [role='alert']").first

    def login(self, email: str, password: str) -> "LoginPage":
        self.email.fill(email)
        self.password.fill(password)
        self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        expect(self.email).to_be_visible()
        expect(self.password).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def expect_error(self) -> None:
        expect(self.error_msg).to_be_visible(timeout=5_000)
