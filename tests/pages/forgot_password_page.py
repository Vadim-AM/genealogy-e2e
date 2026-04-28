"""POMs for forgot-password / reset-password public flows.

Selectors verified against backend/app/main.py:679-797 (28.04 review):
- /account/forgot-password: #fpForm, #email, #fpBtn, #msg
- /account/reset-password:  #rpForm, #password, #password2, #rpBtn, #msg
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class ForgotPasswordPage(BasePage):
    URL = "/account/forgot-password"

    def __init__(self, page: Page):
        super().__init__(page)
        self.form = page.locator("#fpForm")
        self.email = page.locator("#email")
        self.submit_btn = page.locator("#fpBtn")
        self.msg = page.locator("#msg")

    def request_reset(self, email: str) -> "ForgotPasswordPage":
        self.email.fill(email)
        self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        expect(self.form).to_be_visible()
        expect(self.email).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def expect_success_message(self) -> None:
        """`#msg.success` appears for any 2xx response — including the silent
        200 for unknown emails (anti-enumeration)."""
        import re

        expect(self.msg).to_have_class(re.compile(r"\bsuccess\b"))


class ResetPasswordPage(BasePage):
    URL = "/account/reset-password"

    def __init__(self, page: Page):
        super().__init__(page)
        self.form = page.locator("#rpForm")
        self.password = page.locator("#password")
        self.password2 = page.locator("#password2")
        self.submit_btn = page.locator("#rpBtn")
        self.msg = page.locator("#msg")

    def open_with_token(self, token: str) -> "ResetPasswordPage":
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def submit_new_password(self, new_password: str) -> "ResetPasswordPage":
        self.password.fill(new_password)
        self.password2.fill(new_password)
        self.submit_btn.click()
        return self

    def expect_success_message(self) -> None:
        import re

        expect(self.msg).to_have_class(re.compile(r"\bsuccess\b"))
