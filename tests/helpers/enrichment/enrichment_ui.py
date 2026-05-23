"""Enrichment consent dialog UI helpers."""

from __future__ import annotations

from playwright.sync_api import Page

from tests.messages import Buttons, TestData, t


def open_demo_self(page: Page) -> None:
    page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    page.wait_for_load_state("domcontentloaded")


def enrich_button(page: Page):
    return page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)


def consent_dialog(page: Page):
    return page.locator('[data-testid="confirm-dialog"]').first
