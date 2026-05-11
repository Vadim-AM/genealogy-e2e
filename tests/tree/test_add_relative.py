"""Add-relative flow — TC-E2E-008.

Owner opens demo-self profile → clicks "+" beside Sibling group → modal
opens → fills FIO → saves → new person appears in /api/tree.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.person_editor import AddRelativeModal
from tests.pages.profile_panel import ProfilePanel


def test_add_sibling_via_profile_creates_person_and_relationship(
    owner_page: Page, owner_user, tenant_client,
):
    """TC-E2E-008: open demo-self profile → "+" sibling → fill FIO → Save.

    Sibling relation is chosen because it has no `RELATIVE_LIMITS` cap;
    parent slot is already filled by 2 demo parents and the "+" hides there.
    """
    api = tenant_client(owner_user)

    tree_before = api.get(API.TREE)
    tree_before.raise_for_status()
    count_before = len(tree_before.json()["people"])

    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("networkidle")

    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    with owner_page.expect_response("**/api/people**") as resp_info:
        modal.fill_and_save(surname="Тестовый", given="Брат")
    create_response = resp_info.value
    assert create_response.ok, \
        f"POST /api/people failed: {create_response.status} {create_response.text()[:200]}"

    expect(modal.overlay).not_to_be_visible()

    tree_after = api.get(API.TREE)
    tree_after.raise_for_status()
    people_after = tree_after.json()["people"]
    assert len(people_after) == count_before + 1, \
        f"expected exactly one new person; before={count_before}, after={len(people_after)}"

    new_names = {p["name"] for p in people_after}
    assert any("Тестовый" in n and "Брат" in n for n in new_names), \
        f"new sibling 'Тестовый Брат' not in tree names: {new_names}"
