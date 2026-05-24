"""Base page object — shared helpers for every page.

Pattern:
    page = SignupPage(playwright_page).goto()
    page.fill_email("ivan@test").submit()
    page.expect_verification_sent()
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page

from framework.step import step

_CS_WRAPPER = '[data-testid="custom-select"]:has(+ select[data-field="{}"])'
_CS_TRIGGER = '[data-testid="custom-select-trigger"]'
_CS_OPTION = '[data-testid="custom-select-option"][data-value="{}"]'


def custom_select_for(page: Page, field: str) -> Locator:
    """Return the custom-select wrapper for a native select[data-field]."""
    return page.locator(_CS_WRAPPER.format(field))


class BasePage:
    """Common ground for every page object. Subclass overrides URL + locators."""

    URL: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self, *, query: str = "") -> Self:
        """Navigate to the page URL and return self for chaining."""
        with step(f"навигация: переход на {self.URL}"):
            url = self.URL + (f"?{query}" if query else "")
            self.page.goto(url)
        return self

    def goto_and_load(self, *, query: str = "") -> Self:
        """Navigate to the page URL, wait for DOM content loaded, return self."""
        with step(f"навигация: переход и загрузка {self.URL}"):
            self.goto(query=query)
            self.page.wait_for_load_state("domcontentloaded")
        return self

    def wait_for_page_load(self) -> None:
        """Wait for the DOM content to be loaded."""
        with step("ожидание: загрузка DOM"):
            self.page.wait_for_load_state("domcontentloaded")
