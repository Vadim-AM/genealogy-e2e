"""Tree navigation, F5-routing, tabs, search.

Covers: TC-E2E-002 (F5 keeps profile), F-FV-4 tabs.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from framework.step import step
from pages.base import wait_for_authed_shell
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Переключение вкладок обновляет активный класс и контент")
def test_switch_between_tabs(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-4: switching tabs updates active class + content.

    Wave-9: tab `map` скрыт через `hidden=""` (см. BUG-MAP-001). Исключён
    из switcher list — все остальные tabs должны быть кликабельны.
    """
    with step("подготовка: открыть дерево"):
        tree = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)

    with step("проверка: переключение каждой вкладки обновляет active класс"):
        for tab_name in ("sources", "timeline", "about"):
            tree.switch_tab(tab_name)
            tab_loc = getattr(tree, f"tab_{tab_name}")
            expect(tab_loc, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
            expect(owner_page.locator(f"#tab-{tab_name}.active"), ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Поиск по дереву находит демо-персону по имени")
def test_search_returns_results_for_seeded_person(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-5: typing a seeded person's name surfaces matching results.

    `signup_via_api` defaults `full_name="Тестовый Пользователь"` which is
    persisted as the demo-self person's `name`. Searching "Тест" must
    hydrate `#personSearchResults` with `.nav-search-result` items.
    """
    with step("действие: поиск по имени"):
        tree = pages.navigate_to(TreePage)
        owner_page.wait_for_load_state("domcontentloaded")
        tree.search_person("Тест")

    with step("проверка: результаты поиска видны"):
        expect(tree.search_results.first, ErrMsg.search_results_not_visible).to_be_visible()


@allure.title("Обновление страницы F5 сохраняет открытый профиль персоны")
def test_f5_keeps_profile_open(owner_page: Page, pages: PageFactory) -> None:
    """TC-E2E-002: F5 on a profile URL keeps the profile route, не выкидывает в дерево."""
    from pages.profile_panel import ProfilePanel

    with step("действие: открыть профиль и перезагрузить страницу"):
        profile_hash = f"#/p/{TestData.DEMO_PERSON_ID}"
        _ = pages.navigate_to(TreePage)

        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

        owner_page.reload()
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: hash профиля сохранился после F5"):
        assert profile_hash in owner_page.url, f"hash dropped after F5: {owner_page.url}"


@allure.title("Возврат к дереву из профиля по клику на вкладку")
def test_back_to_tree_from_profile(owner_page: Page, pages: PageFactory) -> None:
    """F-PR-4: returning to tree from profile via tab click."""
    from pages.profile_panel import ProfilePanel

    with step("действие: открыть профиль и вернуться в дерево"):
        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        tree = pages.create(TreePage)
        tree.switch_tab("tree")

    with step("проверка: вкладка дерева активна"):
        expect(tree.tab_tree, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
