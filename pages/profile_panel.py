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

from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page, expect

from src.texts import Buttons, FamilyGroups, TestData, t

if TYPE_CHECKING:
    from pages.person_editor import PersonEditor


def open_editor_for(
    page: Page,
    person_id: str = TestData.DEMO_PERSON_ID,
) -> PersonEditor:
    """Navigate to a person's profile and switch to edit mode.

    Returns the ready-to-use PersonEditor. Shared helper — replaces the
    copy-pasted `_open_editor` that lived in three test files.
    """
    from pages.person_editor import PersonEditor

    page.goto(f"/#/p/{person_id}")
    page.wait_for_load_state("domcontentloaded")
    panel = ProfilePanel(page)
    panel.expect_visible()
    panel.open_editor()
    editor = PersonEditor(page)
    editor.expect_visible()
    return editor


class ProfilePanel:
    """Wraps interactions with the open profile of a person."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator('[data-testid="profile-page"]')
        self.title = page.locator('[data-testid="profile-section-title"]')

        # Action buttons via accessible role + name from the catalogue.
        # Robust to onclick→data-action refactors and locale changes.
        self.btn_edit = page.get_by_role("button", name=t(Buttons.EDIT), exact=False)
        self.btn_enrich = page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)
        self.btn_back = page.locator('[data-testid="profile-back"]')

        self.history_block = page.locator("#profileAiHistory")
        self.accepted_facts_block = page.locator("#profileAiAccepted")

    def expect_visible(self) -> None:
        """Assert the profile container is visible."""
        expect(self.container).to_be_visible()

    def open_editor(self) -> PersonEditor:
        """Click Edit and return the person editor."""
        self.btn_edit.click()
        from pages.person_editor import PersonEditor

        return PersonEditor(self.page)

    def trigger_enrichment(self) -> None:
        """Click the enrichment button to start AI search."""
        self.btn_enrich.click()

    def close(self) -> None:
        """Click the back button to close the profile panel."""
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
            self.page.locator('[data-testid="profile-family-group"]')
            .filter(has_text=group_label)
            .locator('[data-testid="profile-rel-add"]')
        )

    def click_add_sibling(self) -> None:
        """Click the add-sibling button in the siblings group."""
        self.add_relative_button(t(FamilyGroups.SIBLINGS)).click()

    def click_add_child(self) -> None:
        """Click the add-child button in the children group."""
        self.add_relative_button(t(FamilyGroups.CHILDREN)).click()

    def click_add_spouse(self) -> None:
        """Click the add-spouse button in the spouse group."""
        self.add_relative_button(t(FamilyGroups.SPOUSE)).click()

    def click_add_parent(self) -> None:
        """Note: visible only when fewer than 2 parents exist (RELATIVE_LIMITS)."""
        self.add_relative_button(t(FamilyGroups.PARENTS)).click()

    # ──────────────────────────────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def navigate_to(page: Page, person_id: str) -> ProfilePanel:
        """Go to a person's profile page and wait for it to render."""
        page.goto(f"/#/p/{person_id}")
        page.wait_for_load_state("domcontentloaded")
        panel = ProfilePanel(page)
        panel.expect_visible()
        return panel

    def click_family_link(self, group_label: str, name_substring: str) -> None:
        """Click a relative's name link inside a family group."""
        group = (
            self.page.locator('[data-testid="profile-family-group"]')
            .filter(has_text=group_label)
        )
        group.locator(
            'a[data-action="open-profile"]'
        ).filter(has_text=name_substring).click()
        expect(self.container).to_be_visible()
