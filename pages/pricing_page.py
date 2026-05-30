"""POM for the public pricing page (/pricing.html).

The page fetches GET /api/tiers/public and renders pricing cards
dynamically via JS. Each card carries ``data-testid="pricing-card"``
with an ``<h2>`` title. The featured tier also carries ``.featured``.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step

from .base import BasePage


class PricingPage(BasePage):
    """Drives the pricing page: navigate, inspect cards."""

    URL = "/pricing.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    @property
    def _cards(self) -> Locator:
        """All pricing card locators."""
        return self.page.locator('[data-testid="pricing-card"], [data-testid="pricing-card-featured"]')

    @property
    def featured(self) -> Locator:
        """Featured pricing card locator."""
        return self.page.locator('[data-testid="pricing-card-featured"]')

    @property
    def card_title_headings(self) -> Locator:
        """All pricing card title locators."""
        return self.page.locator('[data-testid="pricing-card-title"]')

    def cards(self) -> Locator:
        """Return the locator for all pricing cards."""
        return self._cards

    def card_count(self) -> int:
        """Return the number of pricing cards on the page."""
        return self._cards.count()

    def card_titles(self) -> list[str]:
        """Return the list of pricing card title texts."""
        return [h.inner_text().strip() for h in self.card_title_headings.all()]

    def expect_cards_visible(self, count: int = 4) -> None:
        """Assert the expected number of pricing cards are visible."""
        with step("проверка: карточки тарифов видны"):
            expect(self._cards).to_have_count(count)
