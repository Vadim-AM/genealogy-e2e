"""TC-E2E-008: добавление родственника через профиль."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api.person_api import get_tree
from assertions.base import should
from framework.step import step
from pages.add_relative_modal import AddRelativeModal
from pages.profile_panel import ProfilePanel
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Добавление брата/сестры через профиль создаёт персону и связь")
def test_add_sibling_via_profile_creates_person_and_relationship(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Добавить сиблинга через профиль → новая персона в дереве."""
    with step("подготовка: запомнить количество персон в дереве"):
        api = tenant_client(owner_user)
        count_before = len(get_tree(api).people)

    with step("действие: открыть профиль и добавить сиблинга"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

        with owner_page.expect_response("**/api/people**") as resp_info:
            modal.fill_and_save(surname=TestData.ADD_REL_SURNAME, given=TestData.ADD_REL_GIVEN)
        create_response = resp_info.value
        should.playwright_ok(create_response, ErrMsg.pw_response_not_ok)

        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()

    with step("проверка: новая персона появилась в дереве"):
        tree_after = get_tree(api)
        should.have_length(tree_after.people, count_before + 1, ErrMsg.tree_count_wrong)

        new_names = {p.name for p in tree_after.people}
        should.any_match(
            new_names,
            lambda n: TestData.ADD_REL_SURNAME in n and TestData.ADD_REL_GIVEN in n,
            ErrMsg.person_not_in_tree,
        )
