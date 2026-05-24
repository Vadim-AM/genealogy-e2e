"""POMs for forgot-password / reset-password public flows.

Selectors verified against backend/app/main.py:679-797 (28.04 review):
- /account/forgot-password: #fpForm, #email, #fpBtn, #msg
- /account/reset-password:  #rpForm, #password, #password2, #rpBtn, #msg
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from tests._core.messages import Buttons, t

from .base import BasePage


class ForgotPasswordPage(BasePage):
    URL = "/account/forgot-password"

    def __init__(self, page: Page):
        super().__init__(page)
        self.form = page.locator("#fpForm")  # no semantic: form container
        self.email = page.locator("#email")  # no semantic: no <label>
        self.submit_btn = page.get_by_role("button", name=t(Buttons.RESET_PASSWORD))
        self.msg = page.get_by_role("status")

    def request_reset(self, email: str) -> Self:
        """Fill the email and submit the reset request."""
        self.email.fill(email)
        self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        """Assert the forgot-password form elements are visible."""
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
        self.form = page.locator("#rpForm")  # no semantic: form container
        self.password = page.locator("#password")  # no semantic: reset form, no label info
        self.password2 = page.locator("#password2")  # no semantic: no label info
        self.submit_btn = page.locator("#rpBtn")  # no semantic: button text varies by flow
        self.msg = page.get_by_role("status")

    def open_with_token(self, token: str) -> Self:
        """Navigate to the reset page with the given token."""
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def submit_new_password(self, new_password: str) -> Self:
        """Fill both password fields and submit the new password."""
        self.password.fill(new_password)
        self.password2.fill(new_password)
        self.submit_btn.click()
        return self

    def expect_success_message(self) -> None:
        """Assert the status message has the success class."""
        import re

        expect(self.msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_error_message(self) -> None:
        """`#msg.error` — invalid/used token."""
        import re

        expect(self.msg).to_have_class(re.compile(r"\berror\b"))
