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

    def save(self) -> None:
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()
        expect(self.surname).to_be_visible()
        expect(self.given_name).to_be_visible()


class AddRelativeModal:
    """Modal for quickly adding a relative (parent / spouse / child / sibling)
    from the orbit-view "+" buttons. Selectors deferred until reading
    `js/components/add-relative-modal.js` — left as a Wave 3 expansion."""

    def __init__(self, page: Page):
        self.page = page
        # TODO Wave 3: verify against js/components/add-relative-modal.js.
        self.container = page.locator("#addRelativeModal")
        self.surname = self.container.locator('[data-field="surname"]')
        self.given_name = self.container.locator('[data-field="given_name"]')
        self.btn_save = self.container.locator('[data-action="save"]')
        self.btn_cancel = self.container.locator('[data-action="cancel"]')

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()

    def fill_and_save(self, *, surname: str, given: str = "") -> None:
        self.surname.fill(surname)
        if given:
            self.given_name.fill(given)
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()
