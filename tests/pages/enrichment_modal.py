"""POM for the ★ Найти больше enrichment modal.

DEFERRED (Wave 2): container/close-button selectors are guesses. Verify
against `js/components/enrichment-modal.js` and replace OR chains.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.messages import Buttons, t


class EnrichmentModal:
    """Modal that drives AI search, accept/reject hypotheses, view history."""

    def __init__(self, page: Page):
        self.page = page
        # TODO Wave 2: verify modal container selector.
        self.container = page.locator(
            ".enrichment-modal, #enrichmentModal, [role='dialog']"
        ).first
        # TODO Wave 2: replace OR chain with single concrete close-button selector.
        self.btn_close = self.container.get_by_role(
            "button", name=t(Buttons.CLOSE), exact=True
        )
        self.stages_indicator = self.container.locator("[data-stages]").first
        self.archives = self.container.locator("[data-archive]")
        self.hypotheses = self.container.locator("[data-hypothesis]")
        self.btn_accept = self.container.get_by_role(
            "button", name=t(Buttons.ACCEPT), exact=True
        )
        self.btn_reject = self.container.get_by_role(
            "button", name=t(Buttons.REJECT), exact=True
        )
        self.confirm_dialog = page.locator("[role='alertdialog']").first

    def expect_open(self) -> None:
        expect(self.container).to_be_visible()

    def expect_results(self, *, min_archives: int) -> None:
        """Expects at least `min_archives` archive cards rendered.

        Uses count-based assertion (no fallback to substring match), so an
        empty modal that happens to mention 'ЦАМО' in a hint cannot pass.
        """
        expect(self.archives).to_have_count(min_archives)

    def close(self) -> None:
        self.btn_close.click()

    def accept_first_hypothesis(self) -> None:
        self.btn_accept.click()
