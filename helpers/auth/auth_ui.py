"""Auth UI helpers — indicators, links, auth-state polling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def auth_indicator(page: Page) -> Locator:
    """Return the #authIndicator element."""
    return page.locator("#authIndicator")


def auth_name(page: Page) -> Locator:
    """The `.auth-name` span inside the auth indicator (authenticated user's display name)."""
    return auth_indicator(page).locator('[data-testid="auth-user-name"]')


def logout_link(page: Page) -> Locator:
    """Return the logout link inside the auth indicator."""
    return auth_indicator(page).locator('a[data-action="logout"]')


def login_link(page: Page) -> Locator:
    """Guest indicator renders `<a href="/login">Войти</a>` (см. auth-ui.js)."""
    return page.locator('#authIndicator a[href="/login"]')


def wait_for_auth_state(owner_page: Page, *, expected: bool, timeout_ms: int = 5_000) -> None:
    """Poll `window.AUTH.authenticated` until it matches `expected` or timeout.

    `window.AUTH` is set after the initial `/api/auth/me` round-trip; deep
    links can race that read. Asserting the final state instead of the
    instantaneous one keeps the test honest without papering over real bugs.
    """
    owner_page.wait_for_function(
        "(want) => window.AUTH && window.AUTH.authenticated === want",
        arg=expected,
        timeout=timeout_ms,
    )
