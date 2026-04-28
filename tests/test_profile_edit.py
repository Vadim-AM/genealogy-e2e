"""Profile edit through UI — TC-E2E-003 supplement.

Existing test_profile.py asserts canonical-name composition via PATCH;
this test exercises the full UI path: open profile → click edit → fill
field → save → backend reflects change.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.messages import TestData
from tests.pages.person_editor import PersonEditor
from tests.timeouts import TIMEOUTS


@pytest.mark.xfail(
    reason="BUG-EDITOR-001 (found during e2e write): bindPersonEditor sends "
           "`branch=\"\"` on save instead of the existing value "
           "(`subject` for demo-self), causing PATCH /api/people/{id} → 422 "
           "`validation_error` on `branch` enum. Cause: editor's branch <select> "
           "doesn't have its current option pre-selected for seeded persons. "
           "Drop xfail when the editor pre-selects the existing branch value.",
    strict=False,
)
def test_owner_edits_demo_self_summary_through_ui(
    owner_page: Page, owner_user, base_url: str
):
    """Edit `summary` field via the UI and verify backend persisted it.

    Flow: profile route → click `[data-action="profile-edit"]` → wait for
    `#personEditor` → fill `[data-field="summary"]` → click save → assert
    GET /api/people/demo-self returns the new summary.
    """
    summary = "Записано через UI-editor в e2e-тесте"
    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("networkidle")

    edit_btn = owner_page.locator(
        f'[data-action="profile-edit"][data-pid="{TestData.DEMO_PERSON_ID}"]'
    )
    expect(edit_btn).to_be_visible()
    edit_btn.click()

    editor = PersonEditor(owner_page)
    editor.expect_visible()

    editor.summary.fill(summary)
    with owner_page.expect_response(
        f"**/api/people/{TestData.DEMO_PERSON_ID}"
    ) as resp_info:
        editor.save()
    assert resp_info.value.ok, \
        f"PATCH /api/people/{TestData.DEMO_PERSON_ID} returned {resp_info.value.status}"

    # Backend confirms persistence (via owner's session cookies).
    r = httpx.get(
        f"{base_url}/api/people/{TestData.DEMO_PERSON_ID}",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["summary"] == summary, \
        f"summary not persisted: got {r.json().get('summary')!r}"
