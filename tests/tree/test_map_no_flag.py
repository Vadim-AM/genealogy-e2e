"""TC-10.02: Map tab скрыт по умолчанию до включения feature flag."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Вкладка 'Карта' скрыта по умолчанию до включения фичи")
def test_map_tab_is_hidden_by_default(owner_page: Page, pages: PageFactory) -> None:
    """Map tab имеет hidden атрибут и не виден в UI."""
    with step("действие: переход на главную"):
        tree = pages.navigate_to(TreePage)

    with step("проверка: tab map в DOM, но скрыт через hidden"):
        expect(tree.tab_map, ErrMsg.wrong_count).to_have_count(1)
        expect(tree.tab_map, ErrMsg.tab_should_be_hidden).to_be_hidden()
        expect(tree.tab_map, ErrMsg.wrong_attribute).to_have_attribute("hidden", "")
