"""POM for the reusable person editor (used in both profile and admin).

Selectors verified against js/components/person-editor.js (28.04 review).
Container: `.person-editor#personEditor`.
Fields:    `[data-field="<name>"]` — see field list below.
Actions:   `[data-action="save|cancel|delete"]`.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from pages.base import _CS_OPTION, _CS_TRIGGER, custom_select_for
from src.texts import Buttons, t


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
        with step("действие: заполнить ФИО"):
            self.surname.fill(surname)
            self.given_name.fill(given)
            self.patronymic.fill(patronymic)

    def custom_select_wrapper(self, field: str) -> Locator:
        """Return the custom-select wrapper for a given field."""
        return custom_select_for(self.page, field)

    def custom_select_dropdown_locator(self, field: str) -> Locator:
        """Return the dropdown panel inside a custom-select wrapper."""
        return self.custom_select_wrapper(field).locator(
            '[data-testid="custom-select-dropdown"]'  # no semantic: JS widget, no ARIA role
        )

    def focus_custom_select(self, field: str) -> None:
        """Focus the custom-select wrapper for keyboard interaction."""
        with step(f"действие: фокус на custom-select {field!r}"):
            self.custom_select_wrapper(field).focus()

    def press_key(self, key: str) -> None:
        """Press a keyboard key (ArrowDown, Escape, Enter, etc.)."""
        self.page.keyboard.press(key)

    def select_dropdown(self, field: str, value: str) -> None:
        """Pick a value in the customSelect for the given field."""
        with step("действие: выбрать в dropdown"):
            custom = custom_select_for(self.page, field)
            custom.locator(_CS_TRIGGER).click()
            custom.locator(_CS_OPTION.format(value)).click()

    def save(self) -> None:
        """Click the save button to persist editor changes."""
        with step("действие: сохранить персону"):
            self.btn_save.click()

    def cancel(self) -> None:
        """Click cancel to discard editor changes."""
        with step("действие: отменить редактирование"):
            self.btn_cancel.click()

    def delete(self) -> None:
        """Click the delete button to initiate person deletion."""
        with step("действие: нажать Удалить"):
            self.btn_delete.click()

    def fill_maiden_name(self, value: str) -> None:
        """Fill the maiden name field."""
        with step("действие: заполнить девичью фамилию"):
            self.maiden_name.fill(value)

    def fill_summary(self, value: str) -> None:
        """Fill the summary/description field."""
        with step("действие: заполнить описание"):
            self.summary.fill(value)

    def delete_btn_by_role(self) -> Locator:
        """Return a delete button locator scoped to editor via accessible role."""
        return self.container.get_by_role("button", name=t(Buttons.DELETE), exact=False)

    def expect_visible(self) -> None:
        """Assert the editor container and key fields are visible."""
        with step("проверка: редактор виден"):
            expect(self.container).to_be_visible()
            expect(self.surname).to_be_visible()
            expect(self.given_name).to_be_visible()
