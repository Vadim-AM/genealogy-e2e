"""Base page object — shared helpers for every page.

Pattern:
    page = SignupPage(playwright_page).goto()
    page.fill_email("ivan@test").submit()
    page.expect_verification_sent()
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


class BasePage:
    """Common ground for every page object. Subclass overrides URL + locators."""

    URL: str = "/"

    def __init__(self, page: Page):
        self.page = page

    def goto(self, *, query: str = "") -> "BasePage":
        url = self.URL + (f"?{query}" if query else "")
        self.page.goto(url)
        return self

    def expect_no_console_errors(self) -> None:
        """Soft check: no fatal browser console errors. Subscribed at page-level
        in the fixture; this method is a placeholder hook for tests that want
        to assert mid-scenario."""
        pass

    @property
    def title(self) -> str:
        return self.page.title()

    def expect_title_contains(self, fragment: str) -> None:
        expect(self.page).to_have_title(fragment) if "*" not in fragment else None
        # Use partial match
        title = self.page.title()
        assert fragment in title, f"expected '{fragment}' in title, got '{title}'"
