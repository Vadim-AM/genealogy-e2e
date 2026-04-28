"""Profile/person editor through UI — TC-E2E-003, TC-EDITOR-1, TC-EDITOR-2.

Tests for the reusable editor (`#personEditor`) when launched from the
profile page. Covers conditional fields, confirm dialogs, and the full
edit→save→persist round-trip.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.messages import TestData
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
    """TC-EDITOR-2: clicking «Удалить» triggers a `confirm()` whose text
    mentions «Удалить» + irreversibility + «связанные источники и связи».
    Dismissing it must NOT send a DELETE request."""
    # demo-grandpa is non-root (delete button visible) and exists in seed.
    editor = _open_editor(owner_page, person_id="demo-grandpa")

    captured_dialogs: list[str] = []

    def _on_dialog(dialog):
        captured_dialogs.append(dialog.message)
        dialog.dismiss()

    owner_page.once("dialog", _on_dialog)

    delete_responses: list[int] = []
    owner_page.on(
        "response",
        lambda r: delete_responses.append(r.status)
        if r.request.method == "DELETE" and "/api/people/" in r.url
        else None,
    )

    editor.btn_delete.click()
    # Give the dialog handler a moment to fire and the (suppressed) DELETE
    # path to either trigger or not. expect_dialog cannot wait for absence,
    # so we use a short networkidle to settle.
    owner_page.wait_for_load_state("networkidle")

    assert captured_dialogs, "delete must trigger a confirm() dialog"
    msg = captured_dialogs[0]
    assert "Удалить" in msg, f"confirm message must mention 'Удалить': {msg!r}"
    assert "необратим" in msg, (
        f"confirm must call out irreversibility (substring «необратим» "
        f"covers «необратимо/необратимый»): {msg!r}"
    )
    assert "связ" in msg, \
        f"confirm must mention что связи будут отвязаны: {msg!r}"
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
