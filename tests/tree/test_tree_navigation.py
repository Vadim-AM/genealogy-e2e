"""Tree navigation: вкладки, поиск, F5-routing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Переключение вкладок обновляет активный класс и контент")
def test_switch_between_tabs(owner_page: Page, pages: PageFactory) -> None:
    """Переключение вкладок обновляет active class и контент."""
    with step("подготовка: открыть дерево"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()

    with step("проверка: переключение каждой вкладки обновляет active класс"):
        for tab_name in ("sources", "timeline", "about"):
            tree.switch_tab(tab_name)
            tab_loc = getattr(tree, f"tab_{tab_name}")
            expect(tab_loc, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
            tree.expect_tab_content_active(tab_name)


@allure.title("Поиск по дереву находит демо-персону по имени")
def test_search_returns_results_for_seeded_person(owner_page: Page, pages: PageFactory) -> None:
    """Поиск по подстроке имени возвращает matching результаты."""
    with step("действие: поиск по имени"):
        tree = pages.navigate_to(TreePage)
        tree.wait_for_page_load()
        tree.search_person("Тест")

    with step("проверка: результаты поиска видны"):
        expect(tree.search_results.first, ErrMsg.search_results_not_visible).to_be_visible()


@allure.title("Обновление страницы F5 сохраняет открытый профиль персоны")
def test_f5_keeps_profile_open(owner_page: Page, pages: PageFactory) -> None:
    """F5 на profile URL сохраняет hash профиля."""
    with step("действие: открыть профиль и перезагрузить страницу"):
        profile_hash = f"#/p/{TestData.DEMO_PERSON_ID}"
        _ = pages.navigate_to(TreePage)

        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

        owner_page.reload()
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: hash профиля сохранился после F5"):
        should.contain(owner_page.url, profile_hash, ErrMsg.hash_dropped_after_f5)


@allure.title("Возврат к дереву из профиля по клику на вкладку")
def test_back_to_tree_from_profile(owner_page: Page, pages: PageFactory) -> None:
    """Клик по вкладке дерева возвращает из профиля."""
    with step("действие: открыть профиль и вернуться в дерево"):
        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        tree = pages.create(TreePage)
        tree.switch_tab("tree")

    with step("проверка: вкладка дерева активна"):
        expect(tree.tab_tree, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
