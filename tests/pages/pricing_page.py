"""POM for the public pricing page (/pricing.html).

The page fetches GET /api/tiers/public and renders pricing cards
dynamically via JS. Each card carries ``data-testid="pricing-card"``
with an ``<h2>`` title. The featured tier also carries ``.featured``.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class PricingPage:
    """Drives the pricing page: navigate, inspect cards."""

    def __init__(self, page: Page):
        self.page = page
        self._cards = page.locator('[data-testid="pricing-card"], [data-testid="pricing-card-featured"]')
        self.featured = page.locator('[data-testid="pricing-card-featured"]')

    def cards(self) -> Locator:
        """Return the locator for all pricing cards."""
        return self._cards

    def card_count(self) -> int:
        """Return the number of pricing cards on the page."""
        return self._cards.count()

    def card_titles(self) -> list[str]:
        """Return the list of pricing card title texts."""
        headings = self.page.locator('[data-testid="pricing-card-title"]')
        return [h.inner_text().strip() for h in headings.all()]

    def expect_cards_visible(self, count: int = 4) -> None:
        """Assert the expected number of pricing cards are visible."""
        expect(self._cards).to_have_count(count)
