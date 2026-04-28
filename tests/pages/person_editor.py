"""POM for the slide-out person editor + add-relative modal."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class PersonEditor:
    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator(".person-editor, #personEditor, .slide-out").first
        self.surname = page.locator('input[name="surname"], #f_surname').first
        self.given_name = page.locator('input[name="given_name"], #f_given_name').first
        self.patronymic = page.locator('input[name="patronymic"], #f_patronymic').first
        self.maiden = page.locator('input[name="maiden"], #f_maiden').first
        self.birth = page.locator('input[name="birth"], #f_birth').first
        self.death = page.locator('input[name="death"], #f_death').first
        self.death_known = page.locator('input[name="death_known"], #f_death_known').first
        self.notes = page.locator('textarea[name="notes"], #f_notes').first
        self.btn_save = page.get_by_role("button", name="Сохранить", exact=False).first
        self.btn_delete = page.get_by_role("button", name="Удалить", exact=False).first
        self.warning = page.locator(".warning, [role='alert']").first

    def fill_fio(self, surname: str = "", given: str = "", patronymic: str = "") -> None:
        if surname:
            self.surname.fill(surname)
        if given:
            self.given_name.fill(given)
        if patronymic:
            self.patronymic.fill(patronymic)

    def save(self) -> None:
        self.btn_save.click()

    def expect_visible(self) -> None:
        expect(self.surname.or_(self.given_name)).to_be_visible(timeout=10_000)


class AddRelativeModal:
    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator(".add-relative-modal, #addRelativeModal, [role=dialog]").first
        self.title_el = self.container.locator(".modal-title, h2, h3").first
        self.surname = self.container.locator('input[name="surname"], #ar_surname').first
        self.given_name = self.container.locator('input[name="given_name"], #ar_given_name').first
        self.btn_save = self.container.get_by_role("button", name="Сохранить", exact=False).first
        self.btn_cancel = self.container.get_by_role("button", name="Отмена", exact=False).first

    def expect_visible(self) -> None:
        expect(self.container).to_be_visible(timeout=10_000)

    def fill_and_save(self, *, surname: str, given: str = "") -> None:
        if self.surname.count():
            self.surname.fill(surname)
        if self.given_name.count() and given:
            self.given_name.fill(given)
        self.btn_save.click()

    def cancel(self) -> None:
        self.btn_cancel.click()
