"""Profile/person editor through UI — TC-E2E-003, TC-EDITOR-1, TC-EDITOR-2.

Tests for the reusable editor (`#personEditor`) when launched from the
profile page. Covers conditional fields, confirm dialogs, and the full
edit→save→persist round-trip.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.messages import Buttons, TestData, t
from tests.pages.person_editor import PersonEditor
from tests.pages.profile_panel import ProfilePanel
from tests.timeouts import TIMEOUTS


def _open_editor(owner_page: Page, person_id: str = TestData.DEMO_PERSON_ID) -> PersonEditor:
    """Open the given person's profile and switch to edit mode.

    Uses `ProfilePanel` (semantic role-based locators) so we are decoupled
    from current `onclick=` vs future `data-action=` implementation.
    """
    owner_page.goto(f"/#/p/{person_id}")
    owner_page.wait_for_load_state("networkidle")
    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.open_editor()
    editor = PersonEditor(owner_page)
    editor.expect_visible()
    return editor


# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-1: conditional maiden_name field by gender
# ─────────────────────────────────────────────────────────────────────────


def test_maiden_name_visible_only_for_female_gender(owner_page: Page):
    """TC-EDITOR-1: `maiden_name` field is hidden for gender=m, visible for f.
    Switching back to m clears the previously typed value (no orphan data)."""
    editor = _open_editor(owner_page)

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


def test_delete_button_invokes_confirm_dialog(owner_page: Page, owner_user, base_url: str):
    """TC-EDITOR-2: clicking «Удалить» triggers a custom `confirmDialog()`
    whose text mentions «Удалить» + irreversibility + «связанные источники
    и связи». Dismissing it must NOT send a DELETE request.

    После CSP-cleanup (commit dcc5a00) confirm живёт в `confirmDialog`
    из `js/components/confirm-dialog.js` — это custom modal, НЕ browser
    native confirm(). Тест ловит его через DOM-селектор `.confirm-dialog`,
    не через `page.on('dialog')`.
    """
    # demo-grandpa is non-root (delete button visible) and exists in seed.
    editor = _open_editor(owner_page, person_id="demo-grandpa")

    delete_responses: list[int] = []
    owner_page.on(
        "response",
        lambda r: delete_responses.append(r.status)
        if r.request.method == "DELETE" and "/api/people/" in r.url
        else None,
    )

    editor.btn_delete.click()

    # Custom confirm-dialog modal появляется в DOM. Ждём `.confirm-dialog`.
    confirm_dialog = owner_page.locator(".confirm-dialog, [role='alertdialog']").first
    expect(confirm_dialog).to_be_visible(timeout=2_000)

    # Текст confirm-сообщения должен содержать критические маркеры.
    msg = confirm_dialog.inner_text()
    assert "Удалить" in msg, f"confirm must mention 'Удалить': {msg!r}"
    assert "необратим" in msg, (
        f"confirm must call out irreversibility (substring «необратим»): {msg!r}"
    )
    assert "связ" in msg, \
        f"confirm must mention что связи будут отвязаны: {msg!r}"

    # Click «Отмена» — DELETE НЕ должен уйти.
    cancel_btn = confirm_dialog.get_by_role("button", name="Отмена")
    cancel_btn.click()
    owner_page.wait_for_load_state("networkidle")

    assert not delete_responses, \
        f"DELETE must NOT be sent when confirm is dismissed; got: {delete_responses}"

    # Backend still has the person.
    r = httpx.get(
        f"{base_url}/api/people/demo-grandpa",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, \
        f"demo-grandpa should still exist after dismissed confirm; got {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────
# Existing UI-edit regression (was xfail under BUG-EDITOR-002)
# ─────────────────────────────────────────────────────────────────────────


def test_owner_edits_demo_self_summary_through_ui(
    owner_page: Page, owner_user, base_url: str
):
    """Edit `summary` via the editor UI and verify backend persisted it.

    Was xfailed under BUG-EDITOR-002 (bindPersonEditor sent `branch=""`
    on save → PATCH 422). Closed by upstream commit `7e39c57`
    ("fix(editor): skip empty enum fields in PATCH payload"). Now
    a regular regression — keeps surfacing if the empty-enum path
    is reintroduced.
    """
    summary = "Записано через UI-editor в e2e-тесте"
    editor = _open_editor(owner_page)

    editor.summary.fill(summary)
    with owner_page.expect_response(
        f"**/api/people/{TestData.DEMO_PERSON_ID}"
    ) as resp_info:
        editor.save()
    assert resp_info.value.ok, \
        f"PATCH /api/people/{TestData.DEMO_PERSON_ID} returned {resp_info.value.status}"

    r = httpx.get(
        f"{base_url}/api/people/{TestData.DEMO_PERSON_ID}",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["summary"] == summary, \
        f"summary not persisted: got {r.json().get('summary')!r}"



# ─────────────────────────────────────────────────────────────────────────
# TC-EDITOR-3 / X-PR-3 регрессия: «Удалить» в редакторе для root subject
# ─────────────────────────────────────────────────────────────────────────


def test_delete_button_hidden_for_root_subject(owner_page):
    """Editor открытый на корневой subject-карточке не должен показывать
    кнопку «Удалить» — её удаление приводит к потере якоря пространства.

    Was X-PR-3 regression (BUG-UX-002 reopen) until upstream commit
    `1b42498` ("fix(editor): hide «Удалить» в редакторе root-карточки").
    Now regular regression.
    """
    editor = _open_editor(owner_page)
    delete_btn = editor.page.get_by_role(
        "button", name=t(Buttons.DELETE), exact=False
    )
    expect(delete_btn).to_be_hidden()
