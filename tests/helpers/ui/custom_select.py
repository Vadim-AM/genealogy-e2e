"""Custom select wrapper locator helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def custom_select_for(page: Page, field: str) -> Locator:
    """Return the custom-select wrapper locator for a given data-field."""
    return page.locator(
        f'[data-testid="custom-select"]:has(+ select[data-field="{field}"])'
    )
