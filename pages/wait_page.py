"""POM for /wait — waitlist signup landing."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Buttons, Labels, t

from .base import BasePage


class WaitPage(BasePage):
    URL = "/wait"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def email(self) -> Locator:
        """Waitlist email input field."""
        return self.page.get_by_label(t(Labels.WAITLIST_EMAIL))

    @property
    def submit_btn(self) -> Locator:
        """Waitlist submit button."""
        return self.page.get_by_role("button", name=t(Buttons.WAITLIST_SUBMIT))

    @property
    def result(self) -> Locator:
        """no semantic: generic result div"""
        return self.page.locator("#result")

    @property
    def form(self) -> Locator:
        """no semantic: form container"""
        return self.page.locator("#waitForm")

    def submit_email(self, email: str) -> Self:
        """Fill the email and click submit to join the waitlist."""
        with step("действие: отправить email"):
            self.email.fill(email)
            self.submit_btn.click()
        return self

    def expect_success(self) -> None:
        """`#result` becomes visible with non-empty content. Auto-wait via
        Playwright default — no explicit timeout needed."""
        with step("проверка: ожидание подтверждено"):
            expect(self.result).to_be_visible()
            expect(self.result).not_to_have_text("")

    def expect_visible_form(self) -> None:
        """Assert the waitlist form elements are visible."""
        with step("проверка: форма видима"):
            expect(self.form).to_be_visible()
            expect(self.email).to_be_visible()
            expect(self.submit_btn).to_be_visible()

    def is_email_valid(self) -> bool:
        """Return the HTML5 validity state of the email input."""
        return self.page.evaluate("() => document.getElementById('email').checkValidity()")

    def page_content(self) -> str:
        """Return the full HTML content of the page."""
        return self.page.content()
