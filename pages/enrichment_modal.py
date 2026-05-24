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

from playwright.sync_api import Locator, Page, expect

from config.timeouts import TIMEOUTS
from framework.step import step


class EnrichmentModal:
    """Modal driving AI search, accept/reject hypotheses, view history."""

    def __init__(self, page: Page):
        self.page = page

    # ── Locator properties ──────────────────────────────────────────

    @property
    def overlay(self) -> Locator:
        """no semantic: enrichment overlay, no ARIA"""
        return self.page.locator('[data-testid="enrich-overlay"]')

    @property
    def container(self) -> Locator:
        """no semantic: enrichment modal dialog"""
        return self.overlay.locator('[data-testid="enrich-modal"]')

    @property
    def title(self) -> Locator:
        """no semantic: AI result container"""
        return self.container.locator("#enrich-title")

    @property
    def btn_close(self) -> Locator:
        """no semantic: enrichment close button"""
        return self.container.locator('[data-testid="enrich-close"]')

    @property
    def stages_container(self) -> Locator:
        """no semantic: AI progress stages container"""
        return self.container.locator("#enrichStages")

    @property
    def heartbeat(self) -> Locator:
        """no semantic: AI live progress indicator"""
        return self.container.locator("#enrichHeartbeat")

    # Result sections (visible after job completes)

    @property
    def result_body(self) -> Locator:
        """no semantic: AI result body"""
        return self.container.locator('[data-testid="enrich-result-body"]')

    @property
    def archives(self) -> Locator:
        """no semantic: AI archive items"""
        return self.result_body.locator('[data-testid="enrich-archive-item"]')

    @property
    def archive_names(self) -> Locator:
        """no semantic: AI archive name labels"""
        return self.archives.locator('[data-testid="enrich-archive-name"]')

    @property
    def hypotheses(self) -> Locator:
        """no semantic: AI hypothesis items"""
        return self.result_body.locator('[data-testid="enrich-hypothesis"]')

    def expect_open(self) -> None:
        """Assert the enrichment modal is visible."""
        with step("проверка: модалка обогащения открыта"):
            expect(self.container).to_be_visible()

    def wait_results(self) -> None:
        """Block until the (mock) AI job renders its result body."""
        with step("ожидание: результаты AI"):
            expect(self.result_body).to_be_visible(timeout=TIMEOUTS.pw_provision_ms)

    def _hyp_accept_btn(self, hyp: Locator) -> Locator:
        """Кнопка принятия гипотезы."""
        return hyp.locator('[data-hyp-action="accept"]')

    def _hyp_accepted_badge(self, hyp: Locator) -> Locator:
        """Бейдж «принято» на гипотезе."""
        return hyp.locator('[data-testid="enrich-status-accepted"]')

    def accept_first_hypothesis(self) -> None:
        """Accept the first AI hypothesis into the person card."""
        with step("действие: принять гипотезу"):
            first = self.hypotheses.first
            self._hyp_accept_btn(first).click()
            expect(self._hyp_accepted_badge(first)).to_be_visible()

    def expect_results(self, *, min_archives: int) -> None:
        """Hard count assertion — caller knows how many archives the mock fixture
        produces. Substring fallback was removed: a stray "ЦАМО" mention in a
        hint must not pass the test."""
        expect(self.archives).to_have_count(min_archives)

    def stage(self, name: str) -> Locator:
        """Return locator for a progress stage by name."""
        # no semantic: AI result container
        return self.stages_container.locator(f'[data-testid="enrich-stage"][data-stage="{name}"]')

    def close(self) -> None:
        """Close the enrichment modal."""
        with step("действие: закрыть обогащение"):
            self.btn_close.click()
