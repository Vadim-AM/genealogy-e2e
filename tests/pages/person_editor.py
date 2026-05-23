"""POM for the reusable person editor (used in both profile and admin).

Selectors verified against js/components/person-editor.js (28.04 review).
Container: `.person-editor#personEditor`.
Fields:    `[data-field="<name>"]` — see field list below.
Actions:   `[data-action="save|cancel|delete"]`.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.pages.base import custom_select_for


class PersonEditor:
    """Editor form for a Person (FIO, dates, places, status, branch, notes)."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator("#personEditor")

        # FIO group
        self.surname = self.container.locator('[data-field="surname"]')
        self.given_name = self.container.locator('[data-field="given_name"]')
        self.patronymic = self.container.locator('[data-field="patronymic"]')
        self.maiden_name = self.container.locator('[data-field="maiden_name"]')

        # Dates / places
        self.birth = self.container.locator('[data-field="birth"]')
        self.birth_place = self.container.locator('[data-field="birth_place"]')
        self.death = self.container.locator('[data-field="death"]')

        # Misc
        self.badge = self.container.locator('[data-field="badge"]')
        self.summary = self.container.locator('[data-field="summary"]')
        self.notes = self.container.locator('[data-field="notes"]')
        self.gender = self.container.locator('[data-field="gender"]')
        self.branch = self.container.locator('[data-field="branch"]')
        self.status = self.container.locator('[data-field="status"]')

        # Action buttons
        self.btn_save = self.container.locator('[data-action="save"]')
        self.btn_cancel = self.container.locator('[data-action="cancel"]')
        self.btn_delete = self.container.locator('[data-action="delete"]')

        # Inline warning (date-validity, etc.)
        self.warning = self.container.locator('[data-testid="editor-warning"]')

    def fill_fio(self, *, surname: str, given: str, patronymic: str = "") -> None:
        self.surname.fill(surname)
        self.given_name.fill(given)
        self.patronymic.fill(patronymic)

    def select_dropdown(self, field: str, value: str) -> None:
        """Pick a value in the customSelect for the given field."""
        custom = custom_select_for(self.page, field)
        custom.locator('[data-testid="custom-select-trigger"]').click()
        custom.locator(f'[data-testid="custom-select-option"][data-value="{value}"]').click()

    def save(self) -> None:
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()

    def expect_visible(self) -> None:
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
    под FIO-grid'ом (`#addRelExistingResults` role=listbox), «linked» chip
    `.add-rel-linked-chip[data-linked-id]`, unlink-кнопка
    `[data-action="unlink-existing"]`. Та же фича унифицировала
    graph-aware suggestion-cards: `data-action="pick-suggestion"` →
    `pick-existing`, `data-suggestion-id` → `data-person-id` — один
    контракт и для карточек, и для dropdown-строк.
    """

    def __init__(self, page: Page):
        self.page = page
        self.overlay = page.locator('[data-testid="add-rel-overlay"]')
        self.container = self.overlay.locator('[data-testid="add-rel-modal"]')
        self.title = self.container.locator("#add-rel-title")
        self.btn_close = self.container.locator('[data-testid="add-rel-close"]')

        # Fields
        self.surname = self.container.locator("#addRelSurname")
        self.given_name = self.container.locator("#addRelGiven")
        self.patronymic = self.container.locator("#addRelPatronymic")
        self.gender = self.container.locator("#addRelGender")
        self.birth = self.container.locator("#addRelBirth")
        self.death_known = self.container.locator("#addRelDeathKnown")
        self.death = self.container.locator("#addRelDeath")
        self.error = self.container.locator("#addRelError")

        # Actions
        self.btn_save = self.container.locator('[data-action="save"]')
        self.btn_save_and_edit = self.container.locator('[data-action="save-then-edit"]')
        self.btn_cancel = self.container.locator('[data-action="cancel"]')

        # Suggestion block (Фаза 1 — graph-aware dedup): рендерится только если
        # у currentPerson есть siblings с уже-привязанными parents того же пола,
        # что фронт-форма предлагает. Иначе slot пуст.
        self.suggest_slot = self.container.locator("[data-suggest-slot]")
        self.suggest_block = self.container.locator("[data-suggest-block]")
        # Graph-card scoped по классу — `data-action="pick-existing"` теперь
        # общий с dropdown-строками (см. FEATURE-PARENT-SEARCH-001).
        self.suggest_cards = self.container.locator('[data-testid="add-rel-suggest-card"]')
        self.suggest_divider = self.container.locator('[data-testid="add-rel-suggest-divider"]')

        # FEATURE-PARENT-SEARCH-001: inline-autocomplete dropdown + linked-chip.
        self.dropdown = self.container.locator("#addRelExistingResults")
        self.dropdown_rows = self.dropdown.locator('[data-testid="add-rel-existing-row"]')
        self.linked_chip = self.container.locator('[data-testid="add-rel-linked-chip"]')
        self.btn_unlink = self.linked_chip.locator(
            '[data-action="unlink-existing"]'
        )

    def expect_visible(self) -> None:
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
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()

    def close(self) -> None:
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
            '[data-testid="custom-select"]:has(+ select#addRelGender)'
        )
        custom.locator('[data-testid="custom-select-trigger"]').click()
        custom.locator(f'[data-testid="custom-select-option"][data-value="{value}"]').click()

    # ──────────────────────────────────────────────────────────────────
    # Sibling-share-parents checkbox (custom-wrapped `<label class="checkbox">`)
    # ──────────────────────────────────────────────────────────────────

    @property
    def share_parents_input(self) -> Locator:
        return self.container.locator("#addRelSiblingShareParents")

    @property
    def share_parents_label(self) -> Locator:
        """Кастомная обёртка чекбокса — `<label class="checkbox">` со span'ом
        `.checkbox-box`. Нативный input visually-hidden через CSS обёртки,
        поэтому Playwright не может clicknуть его напрямую (element-not-visible).
        Кликаем по label — стандартный HTML toggles bound input."""
        return self.container.locator(
            'label.checkbox:has(#addRelSiblingShareParents)'
        )

    def uncheck_share_parents(self) -> None:
        """Снять отметку «общие родители». No-op если row отсутствует
        (например, у currentPerson нет parents — row не рендерится)."""
        if self.share_parents_input.count() == 0:
            return
        if self.share_parents_input.is_checked():
            self.share_parents_label.click()
            expect(self.share_parents_input).not_to_be_checked()

    # ──────────────────────────────────────────────────────────────────
    # Suggestion-block helpers (Фаза 1 dedup)
    # ──────────────────────────────────────────────────────────────────

    def suggestion_card_by_id(self, person_id: str) -> "Locator":
        """Suggestion card scoped to a specific person.id.

        FEATURE-PARENT-SEARCH-001 унифицировала атрибут: `data-suggestion-id`
        → `data-person-id` (один контракт с dropdown-строками).
        """
        return self.container.locator(
            f'[data-testid="add-rel-suggest-card"][data-person-id="{person_id}"]'
        )

    def click_suggestion(self, person_id: str) -> None:
        """Click a suggestion-card — enters link-mode (chip + readonly form).

        Поведение изменено FEATURE-PARENT-SEARCH-001: клик больше НЕ
        выполняет POST /relationships немедленно, а ставит форму в
        link-mode; подтверждение — через Save (см. `linked_chip`).
        """
        self.suggestion_card_by_id(person_id).click()

    def expect_suggestion_visible(self, person_id: str) -> None:
        expect(self.suggest_block).to_be_visible()
        expect(self.suggestion_card_by_id(person_id)).to_be_visible()

    def expect_no_suggestions(self) -> None:
        """The slot is always present (data-suggest-slot) but should be empty.

        We don't assert slot itself is hidden — it's an always-mounted DIV.
        Instead: zero suggestion-cards and the suggest-block element is absent.
        """
        expect(self.suggest_block).to_have_count(0)
        expect(self.suggest_cards).to_have_count(0)

    # ──────────────────────────────────────────────────────────────────
    # FEATURE-PARENT-SEARCH-001 — inline-autocomplete dropdown + linked-chip
    # ──────────────────────────────────────────────────────────────────

    def search_existing(self, *, surname: str = "", given: str = "") -> None:
        """Type into the FIO inputs to trigger the inline-autocomplete dropdown.

        The dropdown opens automatically once `surname + given` ≥ 2 chars
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
        expect(self.dropdown).to_be_hidden()

    def row_by_person_id(self, person_id: str) -> "Locator":
        """Locator for a dropdown row by the linked person's id."""
        return self.dropdown.locator(
            f'[data-testid="add-rel-existing-row"][data-person-id="{person_id}"]'
        )

    def pick_existing(self, person_id: str) -> None:
        """Click the dropdown row for `person_id` — enters link-mode (chip
        appears, fields go readonly, Save now POSTs only /api/relationships)."""
        self.row_by_person_id(person_id).click()

    def pick_first(self) -> None:
        """Click the first dropdown row (used when the test doesn't care which
        candidate — only that *some* match exists)."""
        self.dropdown_rows.first.click()

    def expect_linked_to(self, person_id: str) -> None:
        """Assert the linked-chip is visible with the given linked-id."""
        expect(self.linked_chip).to_be_visible()
        expect(self.linked_chip).to_have_attribute("data-linked-id", person_id)

    def expect_not_linked(self) -> None:
        expect(self.linked_chip).not_to_be_visible()

    def unlink_existing(self) -> None:
        """Click «Отвязать» on the chip — exits link-mode (form editable)."""
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
