"""POM for the reusable person editor (used in both profile and admin).

Selectors verified against js/components/person-editor.js (28.04 review).
Container: `.person-editor#personEditor`.
Fields:    `[data-field="<name>"]` — see field list below.
Actions:   `[data-action="save|cancel|delete"]`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


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
        self.warning = self.container.locator(".editor-warning")

    def fill_fio(self, *, surname: str, given: str, patronymic: str = "") -> None:
        self.surname.fill(surname)
        self.given_name.fill(given)
        self.patronymic.fill(patronymic)

    def select_dropdown(self, field: str, value: str) -> None:
        """Pick a value in the customSelect for the given field.

        js/components/select.js wraps every native <select> with a styled
        dropdown and hides the native element. The wrapper is inserted as
        previousElementSibling of the native <select>, so we locate it via
        the `:has(+ select[data-field=X])` relation.
        """
        custom = self.container.locator(
            f"div.custom-select:has(+ select[data-field='{field}'])"
        )
        custom.locator(".custom-select-trigger").click()
        custom.locator(f".custom-select-option[data-value='{value}']").click()

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

    Selectors verified against js/components/add-relative-modal.js:
    layout `.add-rel-modal-overlay > .add-rel-modal[role=dialog]`, fields
    by ID (`#addRelSurname`, `#addRelGiven`, ...), actions by
    `[data-action="cancel|save|save-then-edit"]`.
    """

    def __init__(self, page: Page):
        self.page = page
        self.overlay = page.locator(".add-rel-modal-overlay")
        self.container = self.overlay.locator(".add-rel-modal")
        self.title = self.container.locator("#add-rel-title")
        self.btn_close = self.container.locator(".add-rel-close")

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

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()

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

    def cancel(self) -> None:
        self.btn_cancel.click()

    def close(self) -> None:
        self.btn_close.click()
