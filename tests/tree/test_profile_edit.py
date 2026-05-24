"""Profile/person editor through UI — TC-E2E-003, TC-EDITOR-1, TC-EDITOR-2.

Tests for the reusable editor (`#personEditor`) when launched from the
profile page. Covers conditional fields, confirm dialogs, and the full
edit→save→persist round-trip.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from api import person_api, routes
from framework.step import step
from pages.confirm_dialog import ConfirmDialog
from pages.profile_panel import open_editor_for
from src.texts import Buttons, ErrMsg, TestData, t
from src.texts import ConfirmDialog as ConfirmDialogMsg

# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-1: conditional maiden_name field by gender
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Редактор: девичья фамилия видна только для женского пола")
def test_maiden_name_visible_only_for_female_gender(owner_page: Page) -> None:
    """TC-EDITOR-1: `maiden_name` field is hidden for gender=m, visible for f.
    Switching back to m clears the previously typed value (no orphan data)."""
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


# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-2: confirm dialog on delete
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Кнопка 'Удалить' открывает диалог подтверждения с предупреждением")
def test_delete_button_invokes_confirm_dialog(owner_page: Page, owner_user, tenant_client) -> None:
    """TC-EDITOR-2: clicking «Удалить» triggers a custom `confirmDialog()`
    whose text mentions «Удалить» + irreversibility + «связанные источники
    и связи». Dismissing it must NOT send a DELETE request.

    После CSP-cleanup (commit dcc5a00) confirm живёт в `confirmDialog`
    из `js/components/confirm-dialog.js` — это custom modal, НЕ browser
    native confirm(). Тест ловит его через DOM-селектор `.confirm-dialog`,
    не через `page.on('dialog')`.
    """
    with step("подготовка: открыть редактор non-root персоны"):
        editor = open_editor_for(owner_page, person_id="demo-grandpa")

        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: delete_responses.append(r.status)
            if r.request.method == "DELETE" and routes.PEOPLE in r.url
            else None,
        )

    with step("действие: нажать Удалить и проверить текст диалога"):
        editor.btn_delete.click()

        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

        msg = dialog.text()
        assert t(Buttons.DELETE) in msg, f"confirm must mention {t(Buttons.DELETE)!r}: {msg!r}"
        assert t(ConfirmDialogMsg.IRREVERSIBLE) in msg, (
            f"confirm must call out irreversibility ({t(ConfirmDialogMsg.IRREVERSIBLE)!r}): {msg!r}"
        )
        assert t(ConfirmDialogMsg.RELATIONS_KEYWORD) in msg, \
            f"confirm must mention relations ({t(ConfirmDialogMsg.RELATIONS_KEYWORD)!r}): {msg!r}"

    with step("действие: отменить диалог"):
        dialog.cancel()
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: DELETE не отправлен и персона на месте"):
        assert not delete_responses, \
            f"DELETE must NOT be sent when confirm is dismissed; got: {delete_responses}"

        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        assert any(p.id == "demo-grandpa" for p in tree.people), \
            "demo-grandpa should still exist after dismissed confirm"


# ─────────────────────────────────────────────────────────────────────────
# Existing UI-edit regression (was xfail under BUG-EDITOR-002)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Редактирование описания через UI сохраняется в бэкенде")
def test_owner_edits_demo_self_summary_through_ui(
    owner_page: Page, owner_user, tenant_client,
) -> None:
    """Edit `summary` via the editor UI and verify backend persisted it.

    Was xfailed under BUG-EDITOR-002 (bindPersonEditor sent `branch=""`
    on save → PATCH 422). Closed by upstream commit `7e39c57`
    ("fix(editor): skip empty enum fields in PATCH payload"). Now
    a regular regression — keeps surfacing if the empty-enum path
    is reintroduced.
    """
    with step("действие: заполнить summary и сохранить через UI"):
        summary = "Записано через UI-editor в e2e-тесте"
        editor = open_editor_for(owner_page)

        editor.summary.fill(summary)
        with owner_page.expect_response(
            f"**/api/people/{TestData.DEMO_PERSON_ID}"
        ) as resp_info:
            editor.save()
        assert resp_info.value.ok, \
            f"PATCH {routes.person(TestData.DEMO_PERSON_ID)} returned {resp_info.value.status}"

    with step("проверка: summary сохранён в бэкенде"):
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        person = next(p for p in tree.people if p.id == TestData.DEMO_PERSON_ID)
        assert person.summary == summary, \
            f"summary not persisted: got {person.summary!r}"



# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-3 / X-PR-3 регрессия: «Удалить» в редакторе для root subject
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Кнопка удаления скрыта для корневой персоны дерева")
def test_delete_button_hidden_for_root_subject(owner_page) -> None:
    """Editor открытый на корневой subject-карточке не должен показывать
    кнопку «Удалить» — её удаление приводит к потере якоря пространства.

    Was X-PR-3 regression (BUG-UX-002 reopen) until upstream commit
    `1b42498` ("fix(editor): hide «Удалить» в редакторе root-карточки").
    Now regular regression.
    """
    editor = open_editor_for(owner_page)
    delete_btn = editor.page.get_by_role(
        "button", name=t(Buttons.DELETE), exact=False
    )
    expect(delete_btn, ErrMsg.element_should_be_hidden).to_be_hidden()
