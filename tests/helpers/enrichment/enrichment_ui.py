"""Enrichment consent dialog UI helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests._core.messages import Buttons, TestData, t

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def open_demo_self(page: Page) -> None:
    """Navigate to the demo-self profile via hash route."""
    page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    page.wait_for_load_state("domcontentloaded")


def enrich_button(page: Page) -> Locator:
    """Return the enrichment action button."""
    return page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)


def consent_dialog(page: Page) -> Locator:
    """Return the first confirm-dialog locator for AI consent."""
    return page.locator('[data-testid="confirm-dialog"]').first
