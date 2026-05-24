"""Enrichment consent dialog UI helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.confirm_dialog import ConfirmDialog
from pages.profile_panel import ProfilePanel
from src.texts import TestData

if TYPE_CHECKING:
    from playwright.sync_api import Page


def open_demo_self(page: Page) -> ProfilePanel:
    """Navigate to the demo-self profile and return the ProfilePanel POM."""
    return ProfilePanel.navigate_to(page, TestData.DEMO_PERSON_ID)


def get_consent_dialog(page: Page) -> ConfirmDialog:
    """Return the ConfirmDialog POM for AI consent."""
    return ConfirmDialog(page)
