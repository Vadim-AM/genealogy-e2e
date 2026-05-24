"""TC-RESPONSIVE-1: адаптивность ключевых страниц на mobile/tablet viewports."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from src.texts import ErrMsg


@allure.title("Адаптив 375px: регистрация без горизонтального скролла")
def test_signup_card_no_horizontal_scroll_on_iphone_se(mobile_page: Page) -> None:
    """TC-RESPONSIVE-1 (375): signup не вызывает горизонтальный скролл."""
    with step("действие: открыть signup на 375px"):
        mobile_page.goto("/signup")
        mobile_page.wait_for_load_state("domcontentloaded")

    with step("проверка: нет горизонтального скролла"):
        # Не используем «<=» с допусками — браузерный layout deterministic;
        # любое превышение — bug.
        overflow = mobile_page.evaluate(
            "() => ({"
            "  scrollWidth: document.documentElement.scrollWidth,"
            "  clientWidth: document.documentElement.clientWidth,"
            "})"
        )
        should.be_true(overflow["scrollWidth"] <= overflow["clientWidth"], ErrMsg.horizontal_scroll_detected)


@allure.title("Адаптив 375px: иконка показа пароля видна и кликабельна")
def test_signup_password_eye_toggle_visible_on_iphone_se(mobile_page: Page) -> None:
    """TC-RESPONSIVE-1 (375): #pwToggle (eye SVG) виден справа от поля пароля."""
    with step("действие: открыть signup на 375px"):
        mobile_page.goto("/signup")
        mobile_page.wait_for_load_state("domcontentloaded")

    with step("проверка: pwToggle виден и достаточного размера"):
        toggle = mobile_page.locator("#pwToggle")  # no semantic: toggle without ARIA
        expect(toggle, ErrMsg.element_not_visible).to_be_visible()

        box = toggle.bounding_box()
        should.not_none(box, ErrMsg.bounding_box_missing)
        should.be_true(box["width"] >= 16 and box["height"] >= 16, ErrMsg.touch_target_too_small)
        # Right edge внутри viewport (не вылезает).
        should.be_true((box["x"] + box["width"]) <= 375, ErrMsg.element_overflows_viewport)


@allure.title("Адаптив 375px: чекбокс согласия не выходит за экран")
def test_signup_consent_checkbox_label_does_not_overflow_on_iphone_se(
    mobile_page: Page,
) -> None:
    """TC-RESPONSIVE-1 (375): label consent-чекбокса не обрезается."""
    with step("действие: открыть signup на 375px"):
        mobile_page.goto("/signup")
        mobile_page.wait_for_load_state("domcontentloaded")

    with step("проверка: чекбоксы согласия не выходят за viewport"):
        agree_rows = mobile_page.locator('[data-testid="signup-agree-group"]')  # no semantic: checkbox group container
        expect(agree_rows.first, ErrMsg.element_not_visible).to_be_visible()
        count = agree_rows.count()
        should.greater_or_equal(count, 1, ErrMsg.consent_count_wrong)

        for i in range(count):
            row = agree_rows.nth(i)
            box = row.bounding_box()
            should.not_none(box, ErrMsg.bounding_box_missing)
            should.be_true((box["x"] + box["width"]) <= 375, ErrMsg.element_overflows_viewport)


@allure.title("Адаптив 768px: все вкладки видны на iPad portrait")
def test_all_authed_tabs_visible_on_ipad_portrait(tablet_owner_page: Page, soft_check) -> None:
    """TC-RESPONSIVE-1 (768): все основные tabs видны без обрезаний."""
    with step("действие: загрузить главную на 768px"):
        tablet_owner_page.goto("/")
        tablet_owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: все вкладки видны и в пределах viewport"):
        for tab_name in ("tree", "sources", "timeline", "about"):
            tab = tablet_owner_page.locator(f'[data-tab="{tab_name}"]')
            soft_check(tab).to_be_visible()
            box = tab.bounding_box()
            should.not_none(box, ErrMsg.bounding_box_missing)
            should.be_true((box["x"] + box["width"]) <= 768, ErrMsg.tab_overflows_viewport)
