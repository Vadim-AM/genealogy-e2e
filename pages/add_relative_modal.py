"""POM for the add-relative modal (parent / spouse / child / sibling).

Selectors verified against js/components/relatives/shell/*.js.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from pages.base import _CS_OPTION, _CS_TRIGGER


class AddRelativeModal:
    """Modal for adding a relative (parent / spouse / child / sibling) from
    the profile / orbit "+" affordances.

    FEATURE-PARENT-SEARCH-001 unified graph-aware suggestion-cards:
    `data-action="pick-suggestion"` -> `pick-existing`,
    `data-suggestion-id` -> `data-person-id` -- one contract for both
    cards and dropdown rows.
    """

    def __init__(self, page: Page):
        self.page = page

    # ── Container / chrome ────────────────────────────────────────────

    @property
    def overlay(self) -> Locator:
        """no semantic: overlay identified by data-testid, no ARIA"""
        return self.page.locator('[data-testid="add-rel-overlay"]')

    @property
    def container(self) -> Locator:
        """no semantic: modal identified by data-testid, no ARIA"""
        return self.overlay.locator('[data-testid="add-rel-modal"]')

    @property
    def title(self) -> Locator:
        """no semantic: heading without role"""
        return self.container.locator("#add-rel-title")

    @property
    def btn_close(self) -> Locator:
        """no semantic: close button, no accessible name"""
        return self.container.locator('[data-testid="add-rel-close"]')

    # ── Fields ────────────────────────────────────────────────────────

    @property
    def surname(self) -> Locator:
        """no semantic: input without label"""
        return self.container.locator("#addRelSurname")

    @property
    def given_name(self) -> Locator:
        """no semantic: input without label"""
        return self.container.locator("#addRelGiven")

    @property
    def patronymic(self) -> Locator:
        """no semantic: input without label"""
        return self.container.locator("#addRelPatronymic")

    @property
    def gender(self) -> Locator:
        """no semantic: custom select widget, no label"""
        return self.container.locator("#addRelGender")

    @property
    def birth(self) -> Locator:
        """no semantic: input without label"""
        return self.container.locator("#addRelBirth")

    @property
    def death_known(self) -> Locator:
        """no semantic: checkbox without label"""
        return self.container.locator("#addRelDeathKnown")

    @property
    def death(self) -> Locator:
        """no semantic: input without label"""
        return self.container.locator("#addRelDeath")

    @property
    def error(self) -> Locator:
        """no semantic: error text, no ARIA role"""
        return self.container.locator("#addRelError")

    # ── Action buttons ────────────────────────────────────────────────

    @property
    def btn_save(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="save"]')

    @property
    def btn_save_and_edit(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="save-then-edit"]')

    @property
    def btn_cancel(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="cancel"]')

    # ── Suggestion block (graph-aware dedup) ──────────────────────────

    @property
    def suggest_slot(self) -> Locator:
        """no semantic: suggestion slot, no ARIA"""
        return self.container.locator("[data-suggest-slot]")

    @property
    def suggest_block(self) -> Locator:
        """no semantic: suggestion block, no ARIA"""
        return self.container.locator("[data-suggest-block]")

    @property
    def suggest_cards(self) -> Locator:
        """no semantic: card elements, no ARIA role"""
        return self.container.locator('[data-testid="add-rel-suggest-card"]')

    @property
    def suggest_divider(self) -> Locator:
        """no semantic: divider element, no ARIA role"""
        return self.container.locator('[data-testid="add-rel-suggest-divider"]')

    # ── FEATURE-PARENT-SEARCH-001: inline-autocomplete dropdown ──────

    @property
    def dropdown(self) -> Locator:
        """no semantic: listbox without ARIA role"""
        return self.container.locator("#addRelExistingResults")

    @property
    def dropdown_rows(self) -> Locator:
        """no semantic: row elements without ARIA role"""
        return self.dropdown.locator('[data-testid="add-rel-existing-row"]')

    @property
    def linked_chip(self) -> Locator:
        """no semantic: chip element without ARIA role"""
        return self.container.locator('[data-testid="add-rel-linked-chip"]')

    @property
    def btn_unlink(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.linked_chip.locator('[data-action="unlink-existing"]')

    def expect_visible(self) -> None:
        """Assert the add-relative modal is visible."""
        with step("проверка: модалка добавления видима"):
            expect(self.container).to_be_visible()

    def fill_fio(self, *, surname: str, given: str, patronymic: str = "", birth: str = "") -> None:
        """Fill FIO/birth fields WITHOUT clicking save."""
        with step("действие: заполнить ФИО родственника"):
            self.surname.fill(surname)
            self.given_name.fill(given)
            if patronymic:
                self.patronymic.fill(patronymic)
            if birth:
                self.birth.fill(birth)

    def fill_and_save(self, *, surname: str, given: str, patronymic: str = "") -> None:
        """Fill the required FIO fields and click Save."""
        with step("действие: заполнить и сохранить"):
            self.surname.fill(surname)
            self.given_name.fill(given)
            if patronymic:
                self.patronymic.fill(patronymic)
            self.btn_save.click()

    def save(self) -> None:
        """Click Save to create the relative."""
        with step("действие: сохранить родственника"):
            self.btn_save.click()

    def cancel(self) -> None:
        """Click Cancel to dismiss the modal."""
        with step("действие: отменить добавление"):
            self.btn_cancel.click()

    def close(self) -> None:
        """Click the close button to dismiss the modal."""
        with step("действие: закрыть модалку"):
            self.btn_close.click()

    def fill_surname(self, value: str) -> None:
        """Fill the surname field (mid-flow update after unlink)."""
        with step("действие: заполнить фамилию"):
            self.surname.fill(value)

    # ── Gender (custom select wrapped by js/components/select.js) ─────

    _GENDER_SELECT = '[data-testid="custom-select"]:has(+ select#addRelGender)'

    def select_gender(self, value: str) -> None:
        """Pick a gender value ('m'/'f') via the custom-select wrapper."""
        with step("действие: выбрать пол"):
            custom = self.container.locator(self._GENDER_SELECT)
            custom.locator(_CS_TRIGGER).click()
            custom.locator(_CS_OPTION.format(value)).click()

    # ── Sibling-share-parents checkbox ────────────────────────────────

    @property
    def share_parents_input(self) -> Locator:
        """no semantic: hidden checkbox, no label"""
        return self.container.locator("#addRelSiblingShareParents")

    @property
    def share_parents_label(self) -> Locator:
        """no semantic: custom checkbox wrapper, native input hidden"""
        return self.container.locator(
            'label.checkbox:has(#addRelSiblingShareParents)'
        )

    def uncheck_share_parents(self) -> None:
        """Uncheck 'share parents'. No-op if the row is absent."""
        with step("действие: снять авто-родителей"):
            if self.share_parents_input.count() == 0:
                return
            if self.share_parents_input.is_checked():
                self.share_parents_label.click()
                expect(self.share_parents_input).not_to_be_checked()

    # ── Suggestion-block helpers (dedup) ──────────────────────────────

    def suggestion_card_by_id(self, person_id: str) -> Locator:
        """Suggestion card scoped to a specific person.id."""
        return self.container.locator(
            f'[data-testid="add-rel-suggest-card"][data-person-id="{person_id}"]'
        )

    def click_suggestion(self, person_id: str) -> None:
        """Click a suggestion-card -- enters link-mode."""
        with step("действие: выбрать подсказку"):
            self.suggestion_card_by_id(person_id).click()

    def expect_suggestion_visible(self, person_id: str) -> None:
        """Assert the suggestion block and a specific card are visible."""
        with step("проверка: подсказка видна"):
            expect(self.suggest_block).to_be_visible()
            expect(self.suggestion_card_by_id(person_id)).to_be_visible()

    def expect_no_suggestions(self) -> None:
        """Assert no suggestion-cards are present."""
        with step("проверка: подсказок нет"):
            expect(self.suggest_block).to_have_count(0)
            expect(self.suggest_cards).to_have_count(0)

    # ── Inline-autocomplete dropdown + linked-chip ────────────────────

    def search_existing(self, *, surname: str = "", given: str = "") -> None:
        """Type into the FIO inputs to trigger the inline-autocomplete dropdown."""
        with step("действие: поиск существующего"):
            if surname:
                self.surname.fill(surname)
            if given:
                self.given_name.fill(given)

    def expect_dropdown_open(self) -> None:
        """Wait for dropdown to render with at least one row."""
        with step("проверка: dropdown открыт"):
            expect(self.dropdown).to_be_visible()
            expect(self.dropdown_rows.first).to_be_visible()

    def expect_dropdown_closed(self) -> None:
        """Assert the autocomplete dropdown is hidden."""
        with step("проверка: dropdown закрыт"):
            expect(self.dropdown).to_be_hidden()

    def row_by_person_id(self, person_id: str) -> Locator:
        """Locator for a dropdown row by the linked person's id."""
        return self.dropdown.locator(
            f'[data-testid="add-rel-existing-row"][data-person-id="{person_id}"]'
        )

    def pick_existing(self, person_id: str) -> None:
        """Click the dropdown row for `person_id` -- enters link-mode."""
        with step("действие: привязать существующего"):
            self.row_by_person_id(person_id).click()

    def pick_first(self) -> None:
        """Click the first dropdown row."""
        with step("действие: выбрать первого"):
            self.dropdown_rows.first.click()

    def expect_linked_to(self, person_id: str) -> None:
        """Assert the linked-chip is visible with the given linked-id."""
        with step("проверка: привязан"):
            expect(self.linked_chip).to_be_visible()
            expect(self.linked_chip).to_have_attribute("data-linked-id", person_id)

    def expect_not_linked(self) -> None:
        """Assert no linked-chip is visible (create mode)."""
        with step("проверка: не привязан"):
            expect(self.linked_chip).not_to_be_visible()

    def unlink_existing(self) -> None:
        """Click unlink on the chip -- exits link-mode."""
        with step("действие: отвязать"):
            self.btn_unlink.click()

    def expect_field_readonly(self, field: str) -> None:
        """Assert a text field is `readonly` in link-mode."""
        loc_map = {
            "surname": self.surname,
            "given_name": self.given_name,
            "patronymic": self.patronymic,
            "birth": self.birth,
            "death": self.death,
        }
        expect(loc_map[field]).to_have_attribute("readonly", "readonly")

    def pick_first_via_keyboard(self) -> None:
        """Select the first dropdown candidate via ArrowDown + Enter."""
        self.surname.focus()
        self.page.keyboard.press("ArrowDown")
        self.page.keyboard.press("Enter")

    def press_escape(self) -> None:
        """Press Escape while a field is focused (closes dropdown, not modal)."""
        self.surname.focus()
        self.page.keyboard.press("Escape")

    def save_and_expect_response(self, url_pattern: str) -> None:
        """Click Save and wait for a matching network response."""
        with step("действие: сохранить и ожидать ответ"), self.page.expect_response(url_pattern):
            self.btn_save.click()
