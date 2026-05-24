"""Viewport-specific page creation helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Browser, BrowserContext, Page


def make_page(browser: Browser, base_url: str, *, w: int, h: int) -> Iterator[Page]:
    """Create a page with a custom viewport and yield it, then close the context."""
    ctx: BrowserContext = browser.new_context(
        base_url=base_url,
        viewport={"width": w, "height": h},
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    yield page
    ctx.close()
