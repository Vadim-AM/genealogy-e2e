"""Custom select wrapper locator helper."""

from __future__ import annotations

from playwright.sync_api import Page


def custom_select_for(page: Page, field: str):
    return page.locator(
        f'[data-testid="custom-select"]:has(+ select[data-field="{field}"])'
    )
