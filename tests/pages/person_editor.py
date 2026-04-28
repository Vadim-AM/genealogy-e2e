"""POM for the slide-out person editor + add-relative modal.

DEFERRED selectors (Wave 2): the field locators below are educated guesses —
they were authored without reading `js/components/person-editor.js`. Any
class using these POMs is currently brittle. Replace `.first` chains with
single concrete selectors after reading the JS.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.messages import Buttons, t


class PersonEditor:
    def __init__(self, page: Page):
        self.page = page
        # TODO Wave 2: nail down the actual container selector by reading
        # js/components/person-editor.js. Current chain matches one of three
        # plausible shapes — until verified, tests using `expect_visible`
        # may match an unrelated element.
        self.container = page.locator(
            ".person-editor, #personEditor, .slide-out"
        ).first
        self.surname = page.locator('input[name="surname"]')
        self.given_name = page.locator('input[name="given_name"]')
        self.patronymic = page.locator('input[name="patronymic"]')
        self.maiden = page.locator('input[name="maiden"]')
        self.birth = page.locator('input[name="birth"]')
        self.death = page.locator('input[name="death"]')
        self.death_known = page.locator('input[name="death_known"]')
        self.notes = page.locator('textarea[name="notes"]')
        self.btn_save = page.get_by_role("button", name=t(Buttons.SAVE), exact=True)
        self.btn_delete = page.get_by_role("button", name=t(Buttons.DELETE), exact=True)
        self.warning = page.locator("[role='alert']").first

    def fill_fio(self, surname: str, given: str, patronymic: str = "") -> None:
        """All three components are required to make the editor a valid form;
        no silent skips for missing inputs (caller passes empty string explicitly)."""
        self.surname.fill(surname)
        self.given_name.fill(given)
        self.patronymic.fill(patronymic)

    def save(self) -> None:
        self.btn_save.click()

    def expect_visible(self) -> None:
        expect(self.surname).to_be_visible()
        expect(self.given_name).to_be_visible()


class AddRelativeModal:
    def __init__(self, page: Page):
        self.page = page
        # TODO Wave 2: same as PersonEditor — verify container selector against
        # js/components/add-relative-modal.js.
        self.container = page.locator(
            ".add-relative-modal, #addRelativeModal, [role=dialog]"
        ).first
        self.title_el = self.container.locator(".modal-title").first
        self.surname = self.container.locator('input[name="surname"]')
        self.given_name = self.container.locator('input[name="given_name"]')
        self.btn_save = self.container.get_by_role(
            "button", name=t(Buttons.SAVE), exact=True
        )
        self.btn_cancel = self.container.get_by_role(
            "button", name=t(Buttons.CANCEL), exact=True
        )

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible()

    def fill_and_save(self, *, surname: str, given: str = "") -> None:
        """Surname is required; given is optional (modal supports brief entry)."""
        self.surname.fill(surname)
        if given:
            self.given_name.fill(given)
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()
