"""Profile/person editor through UI — TC-E2E-003, TC-EDITOR-1, TC-EDITOR-2.

Tests for the reusable editor (`#personEditor`) when launched from the
profile page. Covers conditional fields, confirm dialogs, and the full
edit→save→persist round-trip.
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import Buttons, ConfirmDialog as ConfirmDialogMsg, TestData, t
from tests.pages.confirm_dialog import ConfirmDialog
from tests.pages.profile_panel import open_editor_for


# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-1: conditional maiden_name field by gender
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Редактор: девичья фамилия видна только для женского пола")
def test_maiden_name_visible_only_for_female_gender(owner_page: Page):
    """TC-EDITOR-1: `maiden_name` field is hidden for gender=m, visible for f.
    Switching back to m clears the previously typed value (no orphan data)."""
    editor = open_editor_for(owner_page)

    # Set gender=m → maiden field's wrapper hides via display:none.
    editor.select_dropdown("gender", "m")
    expect(editor.maiden_name).not_to_be_visible()

    # Set gender=f → wrapper unhides.
    editor.select_dropdown("gender", "f")
    expect(editor.maiden_name).to_be_visible()

    # Type a value in maiden, then switch back to m — value must be cleared.
    editor.maiden_name.fill("Иванова")
    editor.select_dropdown("gender", "m")
    expect(editor.maiden_name).not_to_be_visible()
    expect(editor.maiden_name).to_have_value("")


# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-2: confirm dialog on delete
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Кнопка 'Удалить' открывает диалог подтверждения с предупреждением")
def test_delete_button_invokes_confirm_dialog(owner_page: Page, owner_user, tenant_client):
    """TC-EDITOR-2: clicking «Удалить» triggers a custom `confirmDialog()`
    whose text mentions «Удалить» + irreversibility + «связанные источники
    и связи». Dismissing it must NOT send a DELETE request.

    После CSP-cleanup (commit dcc5a00) confirm живёт в `confirmDialog`
    из `js/components/confirm-dialog.js` — это custom modal, НЕ browser
    native confirm(). Тест ловит его через DOM-селектор `.confirm-dialog`,
    не через `page.on('dialog')`.
    """
    # demo-grandpa is non-root (delete button visible) and exists in seed.
    editor = open_editor_for(owner_page, person_id="demo-grandpa")

    delete_responses: list[int] = []
    owner_page.on(
        "response",
        lambda r: delete_responses.append(r.status)
        if r.request.method == "DELETE" and "/api/people/" in r.url
        else None,
    )

    editor.btn_delete.click()

    dialog = ConfirmDialog(owner_page)
    dialog.expect_visible()

    # Текст confirm-сообщения должен содержать критические маркеры.
    msg = dialog.text()
    assert t(Buttons.DELETE) in msg, f"confirm must mention {t(Buttons.DELETE)!r}: {msg!r}"
    assert t(ConfirmDialogMsg.IRREVERSIBLE) in msg, (
        f"confirm must call out irreversibility ({t(ConfirmDialogMsg.IRREVERSIBLE)!r}): {msg!r}"
    )
    assert t(ConfirmDialogMsg.RELATIONS_KEYWORD) in msg, \
        f"confirm must mention relations ({t(ConfirmDialogMsg.RELATIONS_KEYWORD)!r}): {msg!r}"

    # Click «Отмена» — DELETE НЕ должен уйти.
    dialog.cancel()
    owner_page.wait_for_load_state("domcontentloaded")

    assert not delete_responses, \
        f"DELETE must NOT be sent when confirm is dismissed; got: {delete_responses}"

    # Backend still has the person.
    api = tenant_client(owner_user)
    r = api.get(API.person("demo-grandpa"))
    assert r.status_code == 200, \
        f"demo-grandpa should still exist after dismissed confirm; got {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────
# Existing UI-edit regression (was xfail under BUG-EDITOR-002)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Редактирование описания через UI сохраняется в бэкенде")
def test_owner_edits_demo_self_summary_through_ui(
    owner_page: Page, owner_user, tenant_client,
):
    """Edit `summary` via the editor UI and verify backend persisted it.

    Was xfailed under BUG-EDITOR-002 (bindPersonEditor sent `branch=""`
    on save → PATCH 422). Closed by upstream commit `7e39c57`
    ("fix(editor): skip empty enum fields in PATCH payload"). Now
    a regular regression — keeps surfacing if the empty-enum path
    is reintroduced.
    """
    summary = "Записано через UI-editor в e2e-тесте"
    editor = open_editor_for(owner_page)

    editor.summary.fill(summary)
    with owner_page.expect_response(
        f"**/api/people/{TestData.DEMO_PERSON_ID}"
    ) as resp_info:
        editor.save()
    assert resp_info.value.ok, \
        f"PATCH {API.person(TestData.DEMO_PERSON_ID)} returned {resp_info.value.status}"

    api = tenant_client(owner_user)
    r = api.get(API.person(TestData.DEMO_PERSON_ID))
    r.raise_for_status()
    assert r.json()["summary"] == summary, \
        f"summary not persisted: got {r.json().get('summary')!r}"



# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-3 / X-PR-3 регрессия: «Удалить» в редакторе для root subject
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Кнопка удаления скрыта для корневой персоны дерева")
def test_delete_button_hidden_for_root_subject(owner_page):
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
    expect(delete_btn).to_be_hidden()
