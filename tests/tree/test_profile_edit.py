"""TC-EDITOR: редактор персоны — условные поля, confirm-dialog, round-trip."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import person_api, routes
from assertions.base import should
from framework.step import step
from pages.confirm_dialog import ConfirmDialog
from pages.profile_panel import open_editor_for
from src.texts import Buttons, ErrMsg, TestData, t
from src.texts import ConfirmDialog as ConfirmDialogMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Редактор: девичья фамилия видна только для женского пола")
def test_maiden_name_visible_only_for_female_gender(owner_page: Page) -> None:
    """Девичья фамилия скрыта для m, видна для f, очищается при переключении."""
    with step("подготовка: открыть редактор"):
        editor = open_editor_for(owner_page)

    with step("проверка: maiden скрыто для m, видно для f"):
        editor.select_dropdown("gender", "m")
        expect(editor.maiden_name, ErrMsg.element_should_be_hidden).not_to_be_visible()

        editor.select_dropdown("gender", "f")
        expect(editor.maiden_name, ErrMsg.input_not_visible).to_be_visible()

    with step("проверка: переключение обратно на m очищает maiden"):
        editor.maiden_name.fill("Иванова")
        editor.select_dropdown("gender", "m")
        expect(editor.maiden_name, ErrMsg.element_should_be_hidden).not_to_be_visible()
        expect(editor.maiden_name, ErrMsg.editor_field_wrong).to_have_value("")


@allure.title("Кнопка 'Удалить' открывает диалог подтверждения с предупреждением")
def test_delete_button_invokes_confirm_dialog(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Confirm dialog упоминает удаление, необратимость и связи."""
    with step("подготовка: открыть редактор non-root персоны"):
        editor = open_editor_for(owner_page, person_id="demo-grandpa")

        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: (
                delete_responses.append(r.status) if r.request.method == "DELETE" and routes.PEOPLE in r.url else None
            ),
        )

    with step("действие: нажать Удалить и проверить текст диалога"):
        editor.btn_delete.click()

        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

        msg = dialog.text()
        should.contain(msg, t(Buttons.DELETE), ErrMsg.confirm_text_wrong)
        should.contain(msg, t(ConfirmDialogMsg.IRREVERSIBLE), ErrMsg.confirm_text_wrong)
        should.contain(msg, t(ConfirmDialogMsg.RELATIONS_KEYWORD), ErrMsg.confirm_text_wrong)

    with step("действие: отменить диалог"):
        dialog.cancel_and_settle()

    with step("проверка: DELETE не отправлен и персона на месте"):
        should.be_empty(delete_responses, ErrMsg.delete_sent_on_dismiss)

        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        should.any_match(tree.people, lambda p: p.id == "demo-grandpa", ErrMsg.person_deleted_after_dismiss)


@allure.title("Редактирование описания через UI сохраняется в бэкенде")
def test_owner_edits_demo_self_summary_through_ui(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Summary заполненный через UI сохраняется в бэкенде."""
    with step("действие: заполнить summary и сохранить через UI"):
        summary = "Записано через UI-editor в e2e-тесте"
        editor = open_editor_for(owner_page)

        editor.summary.fill(summary)
        with owner_page.expect_response(f"**/api/people/{TestData.DEMO_PERSON_ID}") as resp_info:
            editor.save()
        should.playwright_ok(resp_info.value, ErrMsg.pw_response_not_ok)

    with step("проверка: summary сохранён в бэкенде"):
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        person = next(p for p in tree.people if p.id == TestData.DEMO_PERSON_ID)
        should.be_equal(person.summary, summary, ErrMsg.summary_not_persisted)


@allure.title("Кнопка удаления скрыта для корневой персоны дерева")
def test_delete_button_hidden_for_root_subject(owner_page: Page) -> None:
    """Кнопка «Удалить» скрыта для root subject."""
    editor = open_editor_for(owner_page)
    expect(editor.delete_btn_by_role(), ErrMsg.element_should_be_hidden).to_be_hidden()
