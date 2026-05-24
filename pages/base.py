"""Base page object — shared helpers for every page.

Pattern:
    page = SignupPage(playwright_page).goto()
    page.fill_email("ivan@test").submit()
    page.expect_verification_sent()
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect


def custom_select_for(page: Page, field: str) -> Locator:
    """Return the custom-select wrapper for a native select[data-field]."""
    return page.locator(f'[data-testid="custom-select"]:has(+ select[data-field="{field}"])')


def wait_for_authed_shell(page: Page) -> None:
    """Block until the authenticated index.html shell has settled.

    Why: `index.html` boots guest-first — `AUTH = {authenticated:false}`
    then `checkAuth()`/`loadData()` resolve async and re-run
    `updateGuestUI()`, which is what un-hides the auth-gated tabs
    (`sources`/`timeline` get an *inline* `display:none` in the guest
    pass that the `.active` class cannot override — only the authed
    re-run clears it). A test that clicks a tab right after
    `domcontentloaded` races that re-run. Under PostgreSQL (slower than
    the retired in-proc SQLite) the window widened enough to flip these
    from flaky-green to consistently red.

    The behavioural settle signal: an orbit card has rendered in
    `#treeContainer`. That can only happen after `/api/tree` resolved,
    which is the same callback that sets `AUTH.authenticated` and runs
    the authed `updateGuestUI()`. Asserting render — not a fixed sleep
    or an internal flag — keeps this robust to refactors (Rule 13).
    """
    expect(
        page.locator('#treeContainer [data-testid="orbit-card"]').first
    ).to_be_visible()


class BasePage:
    """Common ground for every page object. Subclass overrides URL + locators."""

    URL: str = "/"

    def __init__(self, page: Page):
        self.page = page

    def goto(self, *, query: str = "") -> Self:
        """Navigate to the page URL and return self for chaining."""
        url = self.URL + (f"?{query}" if query else "")
        self.page.goto(url)
        return self

    def goto_and_load(self, *, query: str = "") -> Self:
        """Navigate to the page URL, wait for DOM content loaded, return self."""
        self.goto(query=query)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def wait_for_page_load(self) -> None:
        """Wait for the DOM content to be loaded."""
        self.page.wait_for_load_state("domcontentloaded")
