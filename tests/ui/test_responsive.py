"""TC-RESPONSIVE-1: адаптивность ключевых страниц на mobile/tablet viewports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from pages.signup_page import SignupPage
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from playwright.sync_api import Expect


@allure.title("Адаптив 375px: регистрация без горизонтального скролла")
def test_signup_card_no_horizontal_scroll_on_iphone_se(mobile_page: Page) -> None:
    """TC-RESPONSIVE-1 (375): signup не вызывает горизонтальный скролл."""
    with step("действие: открыть signup на 375px"):
        signup = SignupPage(mobile_page).goto_and_load()

    with step("проверка: нет горизонтального скролла"):
        # Не используем допуски — браузерный layout deterministic; любое
        # превышение — bug.
        should.be_false(signup.has_horizontal_overflow(), ErrMsg.horizontal_scroll_detected)


@allure.title("Адаптив 375px: иконка показа пароля видна и кликабельна")
def test_signup_password_eye_toggle_visible_on_iphone_se(mobile_page: Page) -> None:
    """TC-RESPONSIVE-1 (375): #pwToggle (eye SVG) виден справа от поля пароля."""
    with step("действие: открыть signup на 375px"):
        signup = SignupPage(mobile_page).goto_and_load()

    with step("проверка: pwToggle виден и достаточного размера"):
        toggle = signup.password_toggle
        expect(toggle, ErrMsg.element_not_visible).to_be_visible()

        width, height = signup.element_size(toggle)
        should.greater_or_equal(width, 16, ErrMsg.touch_target_too_small)
        should.greater_or_equal(height, 16, ErrMsg.touch_target_too_small)
        # Right edge внутри viewport (не вылезает).
        should.less_or_equal(signup.element_right_edge(toggle), 375, ErrMsg.element_overflows_viewport)


@allure.title("Адаптив 375px: чекбокс согласия не выходит за экран")
def test_signup_consent_checkbox_label_does_not_overflow_on_iphone_se(
    mobile_page: Page,
) -> None:
    """TC-RESPONSIVE-1 (375): label consent-чекбокса не обрезается."""
    with step("действие: открыть signup на 375px"):
        signup = SignupPage(mobile_page).goto_and_load()

    with step("проверка: чекбоксы согласия не выходят за viewport"):
        agree_rows = signup.agree_group
        expect(agree_rows.first, ErrMsg.element_not_visible).to_be_visible()
        count = agree_rows.count()
        should.greater_or_equal(count, 1, ErrMsg.consent_count_wrong)

        for i in range(count):
            row = agree_rows.nth(i)
            should.less_or_equal(
                signup.element_right_edge(row), 375, ErrMsg.element_overflows_viewport
            )


@allure.title("Адаптив 768px: все вкладки видны на iPad portrait")
def test_all_authed_tabs_visible_on_ipad_portrait(tablet_owner_page: Page, soft_check: Expect) -> None:
    """TC-RESPONSIVE-1 (768): все основные tabs видны без обрезаний."""
    with step("действие: загрузить главную на 768px"):
        tree = TreePage(tablet_owner_page).goto_and_load()

    with step("проверка: все вкладки видны и в пределах viewport"):
        for tab_name in ("tree", "sources", "timeline", "about"):
            tab = tree.tab_locator(tab_name)
            soft_check(tab).to_be_visible()
            should.less_or_equal(tree.element_right_edge(tab), 768, ErrMsg.tab_overflows_viewport)
