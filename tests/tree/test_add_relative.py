"""Add-relative flow — TC-E2E-008.

Owner opens demo-self profile → clicks "+" beside Sibling group → modal
opens → fills FIO → saves → new person appears in /api/tree.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from api import routes
from framework.step import step
from pages.person_editor import AddRelativeModal
from pages.profile_panel import ProfilePanel
from src.texts import ErrMsg, TestData


@allure.title("Добавление брата/сестры через профиль создаёт персону и связь")
def test_add_sibling_via_profile_creates_person_and_relationship(
    owner_page: Page, owner_user, tenant_client,
) -> None:
    """TC-E2E-008: open demo-self profile → "+" sibling → fill FIO → Save.

    Sibling relation is chosen because it has no `RELATIVE_LIMITS` cap;
    parent slot is already filled by 2 demo parents and the "+" hides there.
    """
    with step("подготовка: запомнить количество персон в дереве"):
        api = tenant_client(owner_user)
        tree_before = api.get(routes.TREE)
        tree_before.raise_for_status()
        count_before = len(tree_before.json()["people"])

    with step("действие: открыть профиль и добавить сиблинга"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

        with owner_page.expect_response("**/api/people**") as resp_info:
            modal.fill_and_save(surname=TestData.ADD_REL_SURNAME, given=TestData.ADD_REL_GIVEN)
        create_response = resp_info.value
        assert create_response.ok, \
            f"POST /api/people failed: {create_response.status} {create_response.text()[:200]}"

        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()

    with step("проверка: новая персона появилась в дереве"):
        tree_after = api.get(routes.TREE)
        tree_after.raise_for_status()
        people_after = tree_after.json()["people"]
        assert len(people_after) == count_before + 1, \
            f"expected exactly one new person; before={count_before}, after={len(people_after)}"

        new_names = {p["name"] for p in people_after}
        assert any(TestData.ADD_REL_SURNAME in n and TestData.ADD_REL_GIVEN in n for n in new_names), \
            f"new sibling not in tree names: {new_names}"
