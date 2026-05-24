"""POM for the reusable person editor (used in both profile and admin).

Selectors verified against js/components/person-editor.js (28.04 review).
Container: `.person-editor#personEditor`.
Fields:    `[data-field="<name>"]` — see field list below.
Actions:   `[data-action="save|cancel|delete"]`.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from pages.base import custom_select_for


class PersonEditor:
    """Editor form for a Person (FIO, dates, places, status, branch, notes)."""

    def __init__(self, page: Page):
        self.page = page

    # ── Container ─────────────────────────────────────────────────────

    @property
    def container(self) -> Locator:
        """no semantic: form container without role"""
        return self.page.locator("#personEditor")

    # ── FIO group ─────────────────────────────────────────────────────

    @property
    def surname(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="surname"]')

    @property
    def given_name(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="given_name"]')

    @property
    def patronymic(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="patronymic"]')

    @property
    def maiden_name(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="maiden_name"]')

    # ── Dates / places ────────────────────────────────────────────────

    @property
    def birth(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="birth"]')

    @property
    def birth_place(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="birth_place"]')

    @property
    def death(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="death"]')

    # ── Misc fields ───────────────────────────────────────────────────

    @property
    def badge(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="badge"]')

    @property
    def summary(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="summary"]')

    @property
    def notes(self) -> Locator:
        """no semantic: input keyed by data-field, no label"""
        return self.container.locator('[data-field="notes"]')

    @property
    def gender(self) -> Locator:
        """no semantic: custom select widget, no label"""
        return self.container.locator('[data-field="gender"]')

    @property
    def branch(self) -> Locator:
        """no semantic: custom select widget, no label"""
        return self.container.locator('[data-field="branch"]')

    @property
    def status(self) -> Locator:
        """no semantic: custom select widget, no label"""
        return self.container.locator('[data-field="status"]')

    # ── Action buttons ────────────────────────────────────────────────

    @property
    def btn_save(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="save"]')

    @property
    def btn_cancel(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="cancel"]')

    @property
    def btn_delete(self) -> Locator:
        """no semantic: button identified by data-action"""
        return self.container.locator('[data-action="delete"]')

    # ── Inline warning + native select ────────────────────────────────

    @property
    def warning(self) -> Locator:
        """no semantic: warning text, no ARIA role"""
        return self.container.locator('[data-testid="editor-warning"]')

    @property
    def native_gender(self) -> Locator:
        """no semantic: hidden native select"""
        return self.page.locator('select[data-field="gender"]')

    def native_gender_value(self) -> str:
        """Return the current value of the hidden native gender <select>."""
        return self.native_gender.evaluate("(el) => el.value")

    def fill_fio(self, *, surname: str, given: str, patronymic: str = "") -> None:
        """Fill surname, given name, and optionally patronymic."""
        self.surname.fill(surname)
        self.given_name.fill(given)
        self.patronymic.fill(patronymic)

    def select_dropdown(self, field: str, value: str) -> None:
        """Pick a value in the customSelect for the given field."""
        custom = custom_select_for(self.page, field)
        custom.locator('[data-testid="custom-select-trigger"]').click()  # no semantic: custom select trigger, no ARIA
        custom.locator(  # no semantic: custom select option, no ARIA role
            f'[data-testid="custom-select-option"][data-value="{value}"]'
        ).click()

    def save(self) -> None:
        """Click the save button to persist editor changes."""
        self.btn_save.click()

    def cancel(self) -> None:
        """Click cancel to discard editor changes."""
        self.btn_cancel.click()

    def delete_btn_by_role(self) -> Locator:
        """Return a delete button locator scoped to editor via accessible role."""
        from src.texts import Buttons, t
        return self.container.get_by_role("button", name=t(Buttons.DELETE), exact=False)

    def expect_visible(self) -> None:
        """Assert the editor container and key fields are visible."""
        expect(self.container).to_be_visible()
        expect(self.surname).to_be_visible()
        expect(self.given_name).to_be_visible()


class AddRelativeModal:
    """Modal for adding a relative (parent / spouse / child / sibling) from
    the profile / orbit "+" affordances.

    Selectors verified against js/components/relatives/shell/*.js:
    layout `.add-rel-modal-overlay > .add-rel-modal[role=dialog]`, fields
    by ID (`#addRelSurname`, `#addRelGiven`, ...), actions by
    `[data-action="cancel|save|save-then-edit"]`.

    FEATURE-PARENT-SEARCH-001 (link-existing): inline-autocomplete dropdown
    under FIO-grid (`#addRelExistingResults` role=listbox), linked chip
    `.add-rel-linked-chip[data-linked-id]`, unlink button
    `[data-action="unlink-existing"]`. The same feature unified
    graph-aware suggestion-cards: `data-action="pick-suggestion"` ->
    `pick-existing`, `data-suggestion-id` -> `data-person-id` -- one
    contract for both cards and dropdown rows.
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
        expect(self.container).to_be_visible()

    def fill_fio(self, *, surname: str, given: str, patronymic: str = "", birth: str = "") -> None:
        """Fill FIO/birth fields WITHOUT clicking save. Useful for tests that
        want to inspect the suggestion-block state mid-edit.
        """
        self.surname.fill(surname)
        self.given_name.fill(given)
        if patronymic:
            self.patronymic.fill(patronymic)
        if birth:
            self.birth.fill(birth)

    def fill_and_save(self, *, surname: str, given: str, patronymic: str = "") -> None:
        """Fill the required FIO fields and click Save (without going into edit mode).

        Required fields per js/components/add-relative-modal.js: surname, given.
        Patronymic is optional; passing empty string leaves the field unchanged.
        """
        self.surname.fill(surname)
        self.given_name.fill(given)
        if patronymic:
            self.patronymic.fill(patronymic)
        self.btn_save.click()

    def save(self) -> None:
        """Click Save to create the relative."""
        self.btn_save.click()

    def cancel(self) -> None:
        """Click Cancel to dismiss the modal."""
        self.btn_cancel.click()

    def close(self) -> None:
        """Click the close button to dismiss the modal."""
        self.btn_close.click()

    # ──────────────────────────────────────────────────────────────────
    # Gender (custom select wrapped by js/components/select.js)
    # ──────────────────────────────────────────────────────────────────

    def select_gender(self, value: str) -> None:
        """Pick a gender value ('m'/'f') via the custom-select wrapper.

        select.js replaces native <select id="addRelGender"> with a div
        sibling — same pattern as PersonEditor.select_dropdown().
        """
        custom = self.container.locator(
            '[data-testid="custom-select"]:has(+ select#addRelGender)'  # no semantic: custom select widget, no ARIA
        )
        custom.locator('[data-testid="custom-select-trigger"]').click()  # no semantic: custom select trigger, no ARIA
        custom.locator(  # no semantic: custom select option, no ARIA role
            f'[data-testid="custom-select-option"][data-value="{value}"]'
        ).click()

    # ──────────────────────────────────────────────────────────────────
    # Sibling-share-parents checkbox (custom-wrapped `<label class="checkbox">`)
    # ──────────────────────────────────────────────────────────────────

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
        """Uncheck 'share parents'. No-op if the row is absent
        (e.g. currentPerson has no parents -- row is not rendered)."""
        if self.share_parents_input.count() == 0:
            return
        if self.share_parents_input.is_checked():
            self.share_parents_label.click()
            expect(self.share_parents_input).not_to_be_checked()

    # ──────────────────────────────────────────────────────────────────
    # Suggestion-block helpers (dedup)
    # ──────────────────────────────────────────────────────────────────

    def suggestion_card_by_id(self, person_id: str) -> Locator:
        """Suggestion card scoped to a specific person.id.

        FEATURE-PARENT-SEARCH-001 unified the attribute: `data-suggestion-id`
        -> `data-person-id` (one contract with dropdown rows).
        """
        # no semantic: card element, no ARIA role
        return self.container.locator(
            f'[data-testid="add-rel-suggest-card"][data-person-id="{person_id}"]'
        )

    def click_suggestion(self, person_id: str) -> None:
        """Click a suggestion-card -- enters link-mode (chip + readonly form).

        Changed by FEATURE-PARENT-SEARCH-001: click no longer POSTs
        /relationships immediately; it puts the form into link-mode and
        confirmation happens via Save (see `linked_chip`).
        """
        self.suggestion_card_by_id(person_id).click()

    def expect_suggestion_visible(self, person_id: str) -> None:
        """Assert the suggestion block and a specific card are visible."""
        expect(self.suggest_block).to_be_visible()
        expect(self.suggestion_card_by_id(person_id)).to_be_visible()

    def expect_no_suggestions(self) -> None:
        """The slot is always present (data-suggest-slot) but should be empty.

        We don't assert slot itself is hidden -- it's an always-mounted DIV.
        Instead: zero suggestion-cards and the suggest-block element is absent.
        """
        expect(self.suggest_block).to_have_count(0)
        expect(self.suggest_cards).to_have_count(0)

    # ──────────────────────────────────────────────────────────────────
    # FEATURE-PARENT-SEARCH-001 — inline-autocomplete dropdown + linked-chip
    # ──────────────────────────────────────────────────────────────────

    def search_existing(self, *, surname: str = "", given: str = "") -> None:
        """Type into the FIO inputs to trigger the inline-autocomplete dropdown.

        The dropdown opens automatically once `surname + given` >= 2 chars
        (debounce 150ms). Mode must be `create` (default on open) and a
        currentPerson must exist (root-creation has no link target).
        """
        if surname:
            self.surname.fill(surname)
        if given:
            self.given_name.fill(given)

    def expect_dropdown_open(self) -> None:
        """Wait for dropdown to render with at least one row."""
        expect(self.dropdown).to_be_visible()
        expect(self.dropdown_rows.first).to_be_visible()

    def expect_dropdown_closed(self) -> None:
        """Assert the autocomplete dropdown is hidden."""
        expect(self.dropdown).to_be_hidden()

    def row_by_person_id(self, person_id: str) -> Locator:
        """Locator for a dropdown row by the linked person's id."""
        # no semantic: row element, no ARIA role
        return self.dropdown.locator(
            f'[data-testid="add-rel-existing-row"][data-person-id="{person_id}"]'
        )

    def pick_existing(self, person_id: str) -> None:
        """Click the dropdown row for `person_id` -- enters link-mode (chip
        appears, fields go readonly, Save now POSTs only /api/relationships)."""
        self.row_by_person_id(person_id).click()

    def pick_first(self) -> None:
        """Click the first dropdown row (used when the test doesn't care which
        candidate -- only that *some* match exists)."""
        self.dropdown_rows.first.click()

    def expect_linked_to(self, person_id: str) -> None:
        """Assert the linked-chip is visible with the given linked-id."""
        expect(self.linked_chip).to_be_visible()
        expect(self.linked_chip).to_have_attribute("data-linked-id", person_id)

    def expect_not_linked(self) -> None:
        """Assert no linked-chip is visible (create mode)."""
        expect(self.linked_chip).not_to_be_visible()

    def unlink_existing(self) -> None:
        """Click unlink on the chip -- exits link-mode (form editable)."""
        self.btn_unlink.click()

    def expect_field_readonly(self, field: str) -> None:
        """Assert a text field is `readonly` in link-mode.

        `field` is one of: surname, given_name, patronymic, birth, death.
        """
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
        """Click Save and wait for a matching network response.

        Used when the test must assert on the response (e.g. relationships
        or people POST). Returns nothing -- the caller uses the POM's
        overlay assertion to confirm the modal closed.
        """
        with self.page.expect_response(url_pattern):
            self.btn_save.click()
