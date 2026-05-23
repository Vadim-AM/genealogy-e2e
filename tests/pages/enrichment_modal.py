"""POM for the ★ Найти больше enrichment modal.

Selectors verified against js/components/enrichment-modal.js (28.04 review).
Layout:
    .enrich-modal-overlay      ← backdrop
      .enrich-modal[role=dialog]
        .enrich-close          ← × button
        #enrich-title          ← title text
        .enrich-subject        ← person name being enriched
        #enrichStages          ← progress stages container
          .enrich-stage[data-stage="starting|thinking|writing|parsing"]
        #enrichHeartbeat       ← live progress
        .enrich-result-body    ← rendered after job completes
          .enrich-archive-list > li > .enrich-archive-name
          .enrich-hyp-item (AI hypotheses — accept/reject into card)
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.timeouts import TIMEOUTS


class EnrichmentModal:
    """Modal driving AI search, accept/reject hypotheses, view history."""

    def __init__(self, page: Page):
        self.page = page
        self.overlay = page.locator('[data-testid="enrich-overlay"]')
        self.container = self.overlay.locator('[data-testid="enrich-modal"]')
        self.title = self.container.locator("#enrich-title")
        self.btn_close = self.container.locator('[data-testid="enrich-close"]')
        self.stages_container = self.container.locator("#enrichStages")
        self.heartbeat = self.container.locator("#enrichHeartbeat")

        # Result sections (visible after job completes)
        self.result_body = self.container.locator('[data-testid="enrich-result-body"]')
        self.archives = self.result_body.locator('[data-testid="enrich-archive-item"]')
        self.archive_names = self.archives.locator('[data-testid="enrich-archive-name"]')
        self.hypotheses = self.result_body.locator('[data-testid="enrich-hypothesis"]')

    def expect_open(self) -> None:
        expect(self.container).to_be_visible()

    def wait_results(self) -> None:
        """Block until the (mock) AI job renders its result body."""
        expect(self.result_body).to_be_visible(timeout=TIMEOUTS.pw_provision_ms)

    def accept_first_hypothesis(self) -> None:
        """Accept the first AI hypothesis into the person card."""
        first = self.hypotheses.first
        first.locator('[data-hyp-action="accept"]').click()
        expect(first.locator('[data-testid="enrich-status-accepted"]')).to_be_visible()

    def expect_results(self, *, min_archives: int) -> None:
        """Hard count assertion — caller knows how many archives the mock fixture
        produces. Substring fallback was removed: a stray "ЦАМО" mention in a
        hint must not pass the test."""
        expect(self.archives).to_have_count(min_archives)

    def stage(self, name: str):
        """One of 'starting' | 'thinking' | 'writing' | 'parsing'."""
        return self.stages_container.locator(f'[data-testid="enrich-stage"][data-stage="{name}"]')

    def close(self) -> None:
        self.btn_close.click()
