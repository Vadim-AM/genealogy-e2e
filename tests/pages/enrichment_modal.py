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
          (hypotheses container — TODO if needed)
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


class EnrichmentModal:
    """Modal driving AI search, accept/reject hypotheses, view history."""

    def __init__(self, page: Page):
        self.page = page
        self.overlay = page.locator(".enrich-modal-overlay")
        self.container = self.overlay.locator(".enrich-modal")
        self.title = self.container.locator("#enrich-title")
        self.btn_close = self.container.locator(".enrich-close")
        self.stages_container = self.container.locator("#enrichStages")
        self.heartbeat = self.container.locator("#enrichHeartbeat")

        # Result sections (visible after job completes)
        self.result_body = self.container.locator(".enrich-result-body")
        self.archives = self.result_body.locator(".enrich-archive-list > li")
        self.archive_names = self.archives.locator(".enrich-archive-name")

    def expect_open(self) -> None:
        expect(self.container).to_be_visible()

    def expect_results(self, *, min_archives: int) -> None:
        """Hard count assertion — caller knows how many archives the mock fixture
        produces. Substring fallback was removed: a stray "ЦАМО" mention in a
        hint must not pass the test."""
        expect(self.archives).to_have_count(min_archives)

    def stage(self, name: str):
        """One of 'starting' | 'thinking' | 'writing' | 'parsing'."""
        return self.stages_container.locator(f'.enrich-stage[data-stage="{name}"]')

    def close(self) -> None:
        self.btn_close.click()
