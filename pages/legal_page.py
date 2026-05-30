"""POM for static legal pages (/privacy, /terms)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base import BasePage

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class LegalPage(BasePage):
    """Lightweight POM for /privacy and /terms — shared locators."""

    def __init__(self, page: Page, path: str) -> None:
        super().__init__(page)
        self.URL = path

    @property
    def body(self) -> Locator:
        """no semantic: body element"""
        return self.page.locator("body")

    @property
    def headings(self) -> Locator:
        """no semantic: heading elements without specific role"""
        return self.page.locator("h1, h2")

    def body_text(self) -> str:
        """Return the full text content of the body element."""
        return self.body.text_content() or ""

    def heading_count(self) -> int:
        """Return the number of h1/h2 headings on the page."""
        return self.headings.count()

    def title(self) -> str:
        """Return the page title."""
        return self.page.title()
