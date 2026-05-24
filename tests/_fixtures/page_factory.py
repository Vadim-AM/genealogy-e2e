"""PageFactory — type-safe POM creation and navigation.

Usage in tests:
    def test_login(pages: PageFactory):
        login = pages.navigate_to(LoginPage)
        login.login(email, password)

    def test_tree(pages: PageFactory):
        tree = pages.create(TreePage)  # already on the page
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pytest

from tests.pages.base import BasePage

if TYPE_CHECKING:
    from playwright.sync_api import Page

T = TypeVar("T", bound=BasePage)


class PageFactory:
    """Create and navigate to Page Objects bound to the current test page."""

    def __init__(self, page: Page) -> None:
        self._page = page

    def navigate_to(self, page_cls: type[T]) -> T:
        """Create POM instance and navigate to its URL."""
        instance = page_cls(self._page)
        instance.goto()
        return instance

    def create(self, page_cls: type[T]) -> T:
        """Create POM instance without navigation (already on the page)."""
        return page_cls(self._page)

    @property
    def page(self) -> Page:
        """Access the underlying Playwright page."""
        return self._page


@pytest.fixture
def pages(owner_page: Page) -> PageFactory:
    """PageFactory bound to the owner's authenticated page."""
    return PageFactory(owner_page)


@pytest.fixture
def anon_pages(page: Page) -> PageFactory:
    """PageFactory bound to an anonymous (unauthenticated) page."""
    return PageFactory(page)
