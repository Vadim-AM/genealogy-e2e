"""POMs for forgot-password / reset-password public flows.

Selectors verified against backend/app/main.py:679-797 (28.04 review):
- /account/forgot-password: #fpForm, #email, #fpBtn, #msg
- /account/reset-password:  #rpForm, #password, #password2, #rpBtn, #msg
"""

from __future__ import annotations

import re
from typing import Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Buttons, t

from .base import BasePage


class ForgotPasswordPage(BasePage):
    URL = "/account/forgot-password"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def form(self) -> Locator:
        """no semantic: form container"""
        return self.page.locator("#fpForm")

    @property
    def email(self) -> Locator:
        """no semantic: no <label>"""
        return self.page.locator("#email")

    @property
    def submit_btn(self) -> Locator:
        """Submit button for reset link request."""
        return self.page.get_by_role("button", name=t(Buttons.SEND_RESET_LINK))

    @property
    def msg(self) -> Locator:
        """Status message element."""
        return self.page.get_by_role("status")

    def request_reset(self, email: str) -> Self:
        """Fill the email and submit the reset request."""
        with step("действие: запросить сброс пароля"):
            self.email.fill(email)
            self.submit_btn.click()
        return self

    def expect_visible_form(self) -> None:
        """Assert the forgot-password form elements are visible."""
        with step("проверка: форма сброса пароля видима"):
            expect(self.form).to_be_visible()
            expect(self.email).to_be_visible()
            expect(self.submit_btn).to_be_visible()

    def expect_success_message(self) -> None:
        """`#msg.success` appears for any 2xx response -- including the silent
        200 for unknown emails (anti-enumeration)."""
        with step("проверка: сообщение об успехе"):
            expect(self.msg).to_have_class(re.compile(r"\bsuccess\b"))


class ResetPasswordPage(BasePage):
    URL = "/account/reset-password"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def form(self) -> Locator:
        """no semantic: form container"""
        return self.page.locator("#rpForm")

    @property
    def password(self) -> Locator:
        """no semantic: reset form, no label info"""
        return self.page.locator("#password")

    @property
    def password2(self) -> Locator:
        """no semantic: no label info"""
        return self.page.locator("#password2")

    @property
    def submit_btn(self) -> Locator:
        """no semantic: button text varies by flow"""
        return self.page.locator("#rpBtn")

    @property
    def msg(self) -> Locator:
        """Status message element."""
        return self.page.get_by_role("status")

    def open_with_token(self, token: str) -> Self:
        """Navigate to the reset page with the given token."""
        with step("навигация: открыть сброс пароля по токену"):
            self.page.goto(f"{self.URL}?token={token}")
        return self

    def submit_new_password(self, new_password: str) -> Self:
        """Fill both password fields and submit the new password."""
        with step("действие: отправить новый пароль"):
            self.password.fill(new_password)
            self.password2.fill(new_password)
            self.submit_btn.click()
        return self

    def expect_success_message(self) -> None:
        """Assert the status message has the success class."""
        with step("проверка: сброс пароля успешен"):
            expect(self.msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_error_message(self) -> None:
        """`#msg.error` -- invalid/used token."""
        with step("проверка: ошибка сброса пароля"):
            expect(self.msg).to_have_class(re.compile(r"\berror\b"))
