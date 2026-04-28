"""POM for the in-tree person profile panel (slide-out / overlay)."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class ProfilePanel:
    """Wraps interactions with the open profile of a person inside TreePage."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator("#profileContainer, .profile-panel, .profile").first
        self.title = self.container.locator(".section-title, .profile-name, h2").first
        self.btn_enrich = page.get_by_role("button", name="Найти больше", exact=False).first
        self.btn_edit = page.get_by_role("button", name="Редактировать", exact=False).first
        self.btn_delete = page.get_by_role("button", name="Удалить", exact=False).first
        self.history_block = page.locator("[data-block=history], .history-block").first
        self.accepted_facts_block = page.locator("[data-block=accepted], .accepted-facts").first
        self.past_research_block = page.locator("[data-block=past-research], .past-research").first

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible(timeout=10_000)

    def open_editor(self) -> None:
        self.btn_edit.click()

    def trigger_enrichment(self) -> None:
        self.btn_enrich.click()
