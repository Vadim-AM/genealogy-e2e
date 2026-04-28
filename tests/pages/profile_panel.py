"""POM for the in-tree person profile page.

Profile is NOT a slide-out panel — it replaces the contents of
`#treeContainer` with a `.profile-page` block (see js/components/profile.js).
The visible name is rendered in `#tab-tree .section-title` (the tab's main
heading), not inside `.profile-page`.

Selectors verified against js/components/profile.js (28.04 review).
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


class ProfilePanel:
    """Wraps interactions with the open profile of a person."""

    def __init__(self, page: Page):
        self.page = page
        # The profile body lives inside #treeContainer.
        self.container = page.locator(".profile-page")
        # Title is hoisted into the tab heading.
        self.title = page.locator("#tab-tree .section-title")
        # Action buttons (data-action verified in profile.js lines 189, 194, 213).
        self.btn_back = page.locator('[data-action="close-profile"]')
        self.btn_edit = page.locator('[data-action="profile-edit"]')
        self.btn_enrich = page.locator('[data-action="enrich"]')
        # Optional sections (rendered only for editor+ with relevant data).
        self.history_block = page.locator("#profileAiHistory")
        self.accepted_facts_block = page.locator("#profileAiAccepted")

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()

    def open_editor(self) -> None:
        self.btn_edit.click()

    def trigger_enrichment(self) -> None:
        self.btn_enrich.click()

    def close(self) -> None:
        self.btn_back.click()
