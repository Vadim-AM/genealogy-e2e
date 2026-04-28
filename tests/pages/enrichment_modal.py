"""POM for the ★ Найти больше enrichment modal."""

from __future__ import annotations

from playwright.sync_api import Page, expect


class EnrichmentModal:
    """Modal that drives AI search, accept/reject hypotheses, view history."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator(".enrichment-modal, #enrichmentModal, [role=dialog]").first
        self.btn_close = self.container.get_by_role("button", name="Закрыть").or_(
            self.container.locator(".enrich-close, .modal-close")
        ).first
        self.stages_indicator = self.container.locator(".stages, [data-stages]").first
        self.archives = self.container.locator(".archive-item, [data-archive]")
        self.hypotheses = self.container.locator(".hypothesis-item, [data-hypothesis]")
        self.btn_accept = self.container.get_by_role("button", name="Принять", exact=False).first
        self.btn_reject = self.container.get_by_role("button", name="Отклонить", exact=False).first
        self.confirm_dialog = page.locator(".confirm, [role=alertdialog]").first

    def expect_open(self) -> None:
        expect(self.container).to_be_visible(timeout=10_000)

    def expect_results(self) -> None:
        expect(
            self.archives.first.or_(
                self.container.get_by_text("ЦАМО", exact=False).first
            )
        ).to_be_visible(timeout=15_000)

    def close(self) -> None:
        self.btn_close.click()

    def accept_first_hypothesis(self) -> None:
        self.btn_accept.click()
