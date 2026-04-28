"""POM for the in-tree person profile panel (slide-out / overlay).

DEFERRED (Wave 2): container selector is a three-way OR until
`js/components/profile.js` is read. Action buttons are scoped *globally*
on the page, not within the panel — once the container is verified,
re-scope buttons to `self.container.get_by_role(...)`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.messages import Buttons, t


class ProfilePanel:
    """Wraps interactions with the open profile of a person inside TreePage."""

    def __init__(self, page: Page):
        self.page = page
        # TODO Wave 2: verify against js/components/profile.js, replace OR
        # chain with single concrete selector + scope buttons within it.
        self.container = page.locator(
            "#profileContainer, .profile-panel, .profile"
        ).first
        self.title = self.container.locator(".section-title").first
        self.btn_enrich = page.get_by_role("button", name=t(Buttons.ENRICH), exact=True)
        self.btn_edit = page.get_by_role("button", name=t(Buttons.EDIT), exact=True)
        self.btn_delete = page.get_by_role("button", name=t(Buttons.DELETE), exact=True)
        self.history_block = page.locator("[data-block='history']")
        self.accepted_facts_block = page.locator("[data-block='accepted']")
        self.past_research_block = page.locator("[data-block='past-research']")

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()

    def open_editor(self) -> None:
        self.btn_edit.click()

    def trigger_enrichment(self) -> None:
        self.btn_enrich.click()
