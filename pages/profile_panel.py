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

from config.timeouts import TIMEOUTS
from framework.step import step
from pages.person_editor import PersonEditor
from src.texts import Buttons, Enrichment, FamilyGroups, TestData, t


def open_editor_for(
    page: Page,
    person_id: str = TestData.DEMO_PERSON_ID,
) -> PersonEditor:
    """Navigate to a person's profile and switch to edit mode.

    Returns the ready-to-use PersonEditor. Shared helper — replaces the
    copy-pasted `_open_editor` that lived in three test files.
    """

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

    # ── Locator properties ──────────────────────────────────────────

    @property
    def container(self) -> Locator:
        """no semantic: profile page container"""
        return self.page.locator('[data-testid="profile-page"]')

    @property
    def title(self) -> Locator:
        """no semantic: profile section title"""
        return self.page.locator('[data-testid="profile-section-title"]')

    @property
    def btn_edit(self) -> Locator:
        """Кнопка редактирования профиля."""
        return self.page.get_by_role("button", name=t(Buttons.EDIT), exact=False)

    @property
    def btn_enrich(self) -> Locator:
        """Кнопка запуска AI-поиска."""
        return self.page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)

    @property
    def btn_back(self) -> Locator:
        """no semantic: profile back button"""
        return self.page.locator('[data-testid="profile-back"]')

    @property
    def btn_enrich_disabled(self) -> Locator:
        """Кнопка обогащения в отключённом состоянии."""
        return self.page.locator(f'button:has-text("{t(Enrichment.COMING_SOON)}")')

    @property
    def btn_enrich_active(self) -> Locator:
        """no semantic: data-action filter"""
        return self.page.locator('button[data-action="enrich"]:not([disabled])')

    @property
    def history_block(self) -> Locator:
        """no semantic: AI history container"""
        return self.page.locator("#profileAiHistory")

    @property
    def accepted_facts_block(self) -> Locator:
        """no semantic: AI accepted facts container"""
        return self.page.locator("#profileAiAccepted")

    def expect_visible(self) -> None:
        """Assert the profile container is visible."""
        expect(self.container).to_be_visible()

    def open_editor(self) -> PersonEditor:
        """Click Edit and return the person editor."""

        with step("открытие редактора персоны"):
            self.btn_edit.click()
            return PersonEditor(self.page)

    def trigger_enrichment(self) -> None:
        """Click the enrichment button to start AI search."""
        with step("клик «Найти больше»"):
            self.btn_enrich.click()

    def click_enrich_disabled(self) -> None:
        """Force-click the disabled enrichment button (for negative tests)."""
        with step("действие: клик по disabled AI-кнопке"):
            self.btn_enrich_disabled.first.click(force=True)

    def close(self) -> None:
        """Click the back button to close the profile panel."""
        with step("закрытие профиля"):
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
        return self.family_group(group_label).locator(
            '[data-testid="profile-rel-add"]'
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
        with step(f"навигация к профилю {person_id}"):
            page.goto(f"/#/p/{person_id}")
            page.wait_for_load_state("domcontentloaded")
            panel = ProfilePanel(page)
            panel.expect_visible()
            return panel

    @staticmethod
    def navigate_to_fresh(page: Page, person_id: str) -> ProfilePanel:
        """Double-navigation for re-init (init.js has no hashchange listener)."""
        with step(f"навигация к профилю {person_id} (fresh)"):
            page.goto("/")
            page.wait_for_load_state("domcontentloaded")
            page.goto(f"/#/p/{person_id}")
            page.wait_for_load_state("domcontentloaded")
            panel = ProfilePanel(page)
            panel.expect_visible()
            title = page.locator('[data-testid="profile-section-title"]')
            expect(title).not_to_have_text("", timeout=TIMEOUTS.pw_expect_ms)
            return panel

    # ──────────────────────────────────────────────────────────────────
    # Profile data locators (data-testid sections)
    # ──────────────────────────────────────────────────────────────────

    @property
    def dates(self) -> Locator:
        """Locator for `[data-testid="profile-dates"]` inside the profile."""
        # no semantic: data-testid element, no role
        return self.container.locator('[data-testid="profile-dates"]')

    @property
    def place(self) -> Locator:
        """Locator for `[data-testid="profile-place"]` inside the profile."""
        # no semantic: data-testid element, no role
        return self.container.locator('[data-testid="profile-place"]')

    @property
    def story(self) -> Locator:
        """Locator for `[data-testid="profile-story"]` inside the profile."""
        # no semantic: data-testid element, no role
        return self.container.locator('[data-testid="profile-story"]')

    @property
    def family_section(self) -> Locator:
        """Locator for `[data-testid="profile-family"]` inside the profile."""
        # no semantic: data-testid element, no role
        return self.container.locator('[data-testid="profile-family"]')

    @property
    def all_family_links(self) -> Locator:
        """Return all profile-link anchors across the entire family section."""
        return self.family_section.locator('a[data-action="open-profile"]')

    def family_group(self, group_label: str) -> Locator:
        """Return the family-group container scoped by its visible label."""
        # no semantic: data-testid element, no role
        return self.container.locator(
            '[data-testid="profile-family-group"]',
            has_text=group_label,
        )

    def family_links(self, group_label: str) -> Locator:
        """Return all profile-link anchors inside a family group."""
        return self.family_group(group_label).locator(
            'a[data-action="open-profile"]'
        )

    def family_link(self, group_label: str, name_substring: str) -> Locator:
        """Return a specific profile-link anchor inside a family group."""
        return self.family_links(group_label).filter(has_text=name_substring)

    def click_family_link(self, group_label: str, name_substring: str) -> None:
        """Click a relative's name link inside a family group."""
        with step(f"клик по родственнику «{name_substring}»"):
            self.family_link(group_label, name_substring).click()
            expect(self.container).to_be_visible()

    # ──────────────────────────────────────────────────────────────────
    # AI enrichment chips (accepted facts)
    # ──────────────────────────────────────────────────────────────────

    @property
    def accepted_chips(self) -> Locator:
        """Return all accepted AI fact chips in the profile."""
        # no semantic: data-testid element, no role
        return self.accepted_facts_block.locator('[data-testid="profile-ai-chip"]')

    @property
    def chip_revert_btns(self) -> Locator:
        """Кнопки «Снять» на AI-чипах."""
        return self.accepted_chips.locator('[data-testid="profile-ai-chip-revert"]')

    @property
    def revert_confirm_btn(self) -> Locator:
        """Кнопка подтверждения снятия AI-факта."""
        return self.page.get_by_role("button", name=t(Enrichment.REVERT_OK), exact=True)

    def revert_first_chip(self) -> None:
        """Click the revert button on the first accepted AI chip."""
        with step("клик «Снять» на первом AI-чипе"):
            self.chip_revert_btns.first.click()

    def confirm_revert(self) -> None:
        """Click the revert confirmation button in the prompt."""
        with step("подтверждение снятия AI-факта"):
            self.revert_confirm_btn.click()

    @property
    def enrich_disabled_tooltip(self) -> str:
        """Return the title attribute of the disabled enrichment button."""
        return self.btn_enrich_disabled.first.get_attribute("title") or ""

    def wait_for_network_idle(self) -> None:
        """Wait for network to settle after an action."""
        self.page.wait_for_load_state("networkidle")
