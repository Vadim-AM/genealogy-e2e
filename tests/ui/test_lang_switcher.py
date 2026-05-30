"""TC-19.* — Lang switcher до раскатки публичной локализации СКРЫТ."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from assertions.base import should
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Язык: переключатель языка скрыт пока доступен только RU")
def test_lang_switcher_containers_are_hidden_when_only_one_language(anon_pages: PageFactory) -> None:
    """TC-19.*-disabled: `[data-testid="lang-switcher"]` контейнеры (в header и footer)."""
    with step("действие: открыть главную и получить состояния lang-switcher"):
        tree = anon_pages.navigate_to(TreePage)
        states = tree.lang_switcher_states()
        should.not_empty(states, ErrMsg.element_not_visible)

    with step("проверка: все контейнеры пусты и скрыты"):
        for inner_html, display in states:
            should.be_equal(inner_html, "", ErrMsg.lang_switcher_not_empty)
            should.be_equal(display, "none", ErrMsg.lang_switcher_not_hidden)


@allure.title("Язык: атрибут html lang всегда равен ru")
def test_html_lang_attribute_is_ru(anon_pages: PageFactory) -> None:
    """initLang() форс-резолвит в 'ru' (игнорирует localStorage / navigator)."""
    with step("действие: открыть главную"):
        tree = anon_pages.navigate_to(TreePage)

    with step("проверка: html lang равен ru"):
        should.be_equal(tree.html_lang(), "ru", ErrMsg.html_lang_wrong)


@allure.title("Язык: localStorage с en не переключает UI на английский")
def test_localstorage_genealogy_lang_seed_does_not_change_active_lang(anon_pages: PageFactory) -> None:
    """setLang() — no-op при отключённой локализации. Pre-seed до навигации."""
    with step("подготовка: засеять localStorage с en до навигации"):
        tree = anon_pages.create(TreePage)
        tree.seed_local_storage("genealogy_lang", "en")

    with step("действие: открыть главную"):
        tree.goto_and_load()

    with step("проверка: язык остался ru"):
        should.be_equal(tree.html_lang(), "ru", ErrMsg.html_lang_wrong)
