"""Base page object — shared helpers for every page.

Pattern:
    page = SignupPage(playwright_page).goto()
    page.fill_email("ivan@test").submit()
    page.expect_verification_sent()
"""

from __future__ import annotations

from playwright.sync_api import Page


class BasePage:
    """Common ground for every page object. Subclass overrides URL + locators."""

    URL: str = "/"

    def __init__(self, page: Page):
        self.page = page

    def goto(self, *, query: str = "") -> "BasePage":
        url = self.URL + (f"?{query}" if query else "")
        self.page.goto(url)
        return self
