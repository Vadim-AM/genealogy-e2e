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

from pages.base import BasePage

if TYPE_CHECKING:
    from collections.abc import Callable

    from playwright.sync_api import Page

T = TypeVar("T")
B = TypeVar("B", bound=BasePage)


class PageFactory:
    """Create and navigate to Page Objects bound to the current test page."""

    def __init__(self, page: Page) -> None:
        self._page = page

    def navigate_to(self, page_cls: type[B]) -> B:
        """Create a full-page POM and navigate to its URL (requires goto/URL)."""
        instance = page_cls(self._page)
        instance.goto()
        return instance

    def create(self, page_cls: Callable[[Page], T]) -> T:
        """Create a POM or component bound to the current page (no navigation).

        Accepts both BasePage subclasses and page-bound components
        (modals, panels, dialogs) whose __init__ takes the Page.
        """
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


@pytest.fixture
def make_pages() -> Callable[[Page], PageFactory]:
    """Return a PageFactory builder for an arbitrary page.

    Used by custom-viewport tests (mobile/tablet) and manual BrowserContexts,
    which the page-bound `pages`/`anon_pages` fixtures cannot serve.
    """
    return PageFactory
