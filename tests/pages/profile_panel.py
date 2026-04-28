"""POM for the in-tree person profile page.

Profile is NOT a slide-out panel — it replaces the contents of
`#treeContainer` with a `.profile-page` block (see js/components/profile.js).
The visible name is rendered in `#tab-tree .section-title` (the tab's main
heading), not inside `.profile-page`.

Locators are role/text-based (semantic), not bound to `onclick=` substrings —
that keeps tests stable when the BUG-SEC-002 sweep moves these handlers to
`data-action=` event delegation.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.messages import Buttons, FamilyGroups, t


class ProfilePanel:
    """Wraps interactions with the open profile of a person."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator(".profile-page")
        self.title = page.locator("#tab-tree .section-title")

        # Action buttons via accessible role + name from the catalogue.
        # Robust to onclick→data-action refactors and locale changes.
        self.btn_edit = page.get_by_role("button", name=t(Buttons.EDIT), exact=False)
        self.btn_enrich = page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)
        # Back: `← назад к дереву` — class is the most stable handle.
        self.btn_back = page.locator(".profile-back")

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

    # ──────────────────────────────────────────────────────────────────
    # Add-relative
    # ──────────────────────────────────────────────────────────────────

    def add_relative_button(self, group_label: str) -> Locator:
        """Return the `+` locator scoped to a family-group by its visible label.

        `group_label` is the catalogue value (e.g. `t(FamilyGroups.SIBLINGS)`).
        Scope: `.profile-family-group` containing that label → `.profile-rel-add`.
        Substring match on label so «Супруг(а)» / «Супруг» both work.
        """
        return (
            self.page.locator(".profile-family-group")
            .filter(has_text=group_label)
            .locator(".profile-rel-add")
        )

    def click_add_sibling(self) -> None:
        self.add_relative_button(t(FamilyGroups.SIBLINGS)).click()

    def click_add_child(self) -> None:
        self.add_relative_button(t(FamilyGroups.CHILDREN)).click()

    def click_add_spouse(self) -> None:
        self.add_relative_button(t(FamilyGroups.SPOUSE)).click()

    def click_add_parent(self) -> None:
        """Note: visible only when fewer than 2 parents exist (RELATIVE_LIMITS)."""
        self.add_relative_button(t(FamilyGroups.PARENTS)).click()
