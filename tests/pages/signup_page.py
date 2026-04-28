"""POM for /signup."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from .base import BasePage


class SignupPage(BasePage):
    URL = "/signup"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator("#email")
        self.password = page.locator("#password")
        self.full_name = page.locator("#full_name")
        self.birth_year = page.locator("#birth_year")
        self.honeypot = page.locator("#website")
        self.agree = page.locator("#agree")
        self.submit_btn = page.locator("#signupBtn")
        self.password_toggle = page.locator("#pwToggle")
        self.password_strength = page.locator(".pw-meter")
        self.signup_msg = page.locator("#signupMsg")

    def fill_required(
        self,
        *,
        email: str,
        password: str,
        full_name: str = "Тестовый Пользователь",
        birth_year: int | None = None,
        agree: bool = True,
    ) -> "SignupPage":
        self.email.fill(email)
        self.password.fill(password)
        self.full_name.fill(full_name)
        if birth_year is not None:
            self.birth_year.fill(str(birth_year))
        if agree:
            self.agree.check()
        return self

    def submit(self) -> "SignupPage":
        self.submit_btn.click()
        return self

    def expect_verification_message(self) -> None:
        """After successful submit `#signupMsg` gets the `success` class added.
        Regex match — survives copy / class additions."""
        expect(self.signup_msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_visible_form(self) -> None:
        expect(self.email).to_be_visible()
        expect(self.password).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def soft_check_form_basics(self, soft) -> None:
        """Smoke for X-SU-1..11: input attrs, autocomplete, required."""
        soft(self.email).to_have_attribute("type", "email")
        soft(self.email).to_have_attribute("autocomplete", "email")
        soft(self.email).to_have_attribute("required", "")
        soft(self.password).to_have_attribute("type", "password")
        soft(self.password).to_have_attribute("autocomplete", "new-password")
        soft(self.full_name).to_have_attribute("required", "")
        soft(self.honeypot).to_have_attribute("tabindex", "-1")
        soft(self.submit_btn).to_have_attribute("type", "submit")
