"""TC-19.* — Lang switcher до раскатки публичной локализации СКРЫТ."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from assertions.base import should
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory


@allure.title("Язык: переключатель языка скрыт пока доступен только RU")
def test_lang_switcher_containers_are_hidden_when_only_one_language(page: Page, anon_pages: PageFactory) -> None:
    """TC-19.*-disabled: `[data-testid="lang-switcher"]` контейнеры (в header и footer)."""
    with step("действие: открыть главную и найти lang-switcher контейнеры"):
        _ = anon_pages.navigate_to(TreePage)

        containers = page.locator('[data-testid="lang-switcher"]').all()  # no semantic: switcher container, no role
        should.be_true(containers, ErrMsg.element_not_visible)

    with step("проверка: все контейнеры пусты и скрыты"):
        for idx, container in enumerate(containers):
            inner_html = container.evaluate("(el) => el.innerHTML.trim()")
            display = container.evaluate("(el) => getComputedStyle(el).display")
            should.be_equal(inner_html, "", ErrMsg.lang_switcher_not_empty)
            should.be_equal(display, "none", ErrMsg.lang_switcher_not_hidden)


@allure.title("Язык: атрибут html lang всегда равен ru")
def test_html_lang_attribute_is_ru(page: Page, anon_pages: PageFactory) -> None:
    """initLang() форс-резолвит в 'ru' (igноривает localStorage / navigator)."""
    with step("действие: открыть главную"):
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: html lang равен ru"):
        html_lang = page.evaluate("() => document.documentElement.lang")
        should.be_equal(html_lang, "ru", ErrMsg.html_lang_wrong)


@allure.title("Язык: localStorage с en не переключает UI на английский")
def test_localstorage_genealogy_lang_seed_does_not_change_active_lang(page: Page, anon_pages: PageFactory) -> None:
    """setLang() — no-op при отключённой локализации. Pre-seed."""
    with step("подготовка: засеять localStorage с en"):
        # Pre-seed localStorage ДО навигации, через init script
        page.add_init_script("try { localStorage.setItem('genealogy_lang', 'en'); } catch (e) {}")

    with step("действие: открыть главную"):
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: язык остался ru"):
        html_lang = page.evaluate("() => document.documentElement.lang")
        should.be_equal(html_lang, "ru", ErrMsg.html_lang_wrong)
