"""TC-RESPONSIVE-1: адаптивность ключевых страниц на mobile/tablet viewports.

Default conftest viewport — 1440×900 (desktop). Этот файл создаёт
свои контексты с другими размерами — тестировать на одном профиле
бессмысленно (проблемы layout проявляются именно на узком).

Источник критериев — `docs/test-plan.md` TC-RESPONSIVE-1:

  - 375×812 (iPhone SE): signup card на полную ширину, нет
    горизонтального скролла, eye-toggle SVG виден.
  - 768×1024 (iPad portrait): все 5 tabs главной видны без
    обрезаний; орбитальное древо центрируется.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests.messages import TestData


# ─────────────────────────────────────────────────────────────────────────
# 375×812 — iPhone SE
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Адаптив 375px: регистрация без горизонтального скролла")
def test_signup_card_no_horizontal_scroll_on_iphone_se(mobile_page: Page):
    """TC-RESPONSIVE-1 (375): signup не вызывает горизонтальный скролл.

    Любое поле/кнопка, выходящее за viewport, ломает первое впечатление
    и conversion на мобильных (>50% трафика). Проверяем DOM-инвариант:
    documentElement.scrollWidth ≤ viewport.width.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("domcontentloaded")

    # Не используем «<=» с допусками — браузерный layout deterministic;
    # любое превышение — bug.
    overflow = mobile_page.evaluate(
        "() => ({"
        "  scrollWidth: document.documentElement.scrollWidth,"
        "  clientWidth: document.documentElement.clientWidth,"
        "})"
    )
    assert overflow["scrollWidth"] <= overflow["clientWidth"], (
        f"horizontal scroll detected on /signup at 375px: "
        f"scrollWidth={overflow['scrollWidth']} > clientWidth={overflow['clientWidth']}"
    )


@allure.title("Адаптив 375px: иконка показа пароля видна и кликабельна")
def test_signup_password_eye_toggle_visible_on_iphone_se(mobile_page: Page):
    """TC-RESPONSIVE-1 (375): #pwToggle (eye SVG) виден справа от поля пароля.

    На мобильных пользователю особенно важно видеть pw-toggle —
    клавиатура часто скрывает hint, а ошибка ввода без визуальной
    проверки бьёт по конверсии.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("domcontentloaded")

    toggle = mobile_page.locator("#pwToggle")
    expect(toggle).to_be_visible()

    box = toggle.bounding_box()
    assert box is not None, "pwToggle has no bounding box (display:none?)"
    assert box["width"] >= 16 and box["height"] >= 16, (
        f"pwToggle hit-area too small for touch: {box}"
    )
    # Right edge внутри viewport (не вылезает).
    assert (box["x"] + box["width"]) <= 375, (
        f"pwToggle overflows viewport on iPhone SE: "
        f"right_edge={box['x'] + box['width']} > 375"
    )


@allure.title("Адаптив 375px: чекбокс согласия не выходит за экран")
def test_signup_consent_checkbox_label_does_not_overflow_on_iphone_se(
    mobile_page: Page,
):
    """TC-RESPONSIVE-1 (375): label consent-чекбокса не обрезается.

    Wave-9 (май 2026): privacy/cross-border объединены с `terms_accepted`,
    в форме остался один `[data-testid="signup-agree-group"]` чекбокс. Должен укладываться в 375px.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("domcontentloaded")

    agree_rows = mobile_page.locator('[data-testid="signup-agree-group"]')
    expect(agree_rows.first).to_be_visible()
    count = agree_rows.count()
    assert count >= 1, f'Ожидали ≥1 [data-testid="signup-agree-group"] блок, нашли {count}'

    for i in range(count):
        row = agree_rows.nth(i)
        box = row.bounding_box()
        assert box is not None, f'[data-testid="signup-agree-group"][{i}] not visible'
        assert (box["x"] + box["width"]) <= 375, (
            f'[data-testid="signup-agree-group"][{i}] row overflows iPhone SE width: '
            f"right_edge={box['x'] + box['width']} > 375"
        )


# ─────────────────────────────────────────────────────────────────────────
# 768×1024 — iPad portrait
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Адаптив 768px: все вкладки видны на iPad portrait")
def test_all_authed_tabs_visible_on_ipad_portrait(tablet_owner_page: Page, soft_check):
    """TC-RESPONSIVE-1 (768): все основные tabs видны без обрезаний.

    Wave-9: tab `map` скрыт через `hidden` (см. BUG-MAP-001). Остальные 4
    tabs (tree/sources/timeline/about) должны быть видны authenticated owner'у.
    """
    tablet_owner_page.goto("/")
    tablet_owner_page.wait_for_load_state("domcontentloaded")

    for tab_name in ("tree", "sources", "timeline", "about"):
        tab = tablet_owner_page.locator(f'[data-tab="{tab_name}"]')
        soft_check(tab).to_be_visible()
        box = tab.bounding_box()
        assert box is not None, f"tab {tab_name!r} not measurable"
        assert (box["x"] + box["width"]) <= 768, (
            f"tab {tab_name!r} overflows viewport at 768px: "
            f"right_edge={box['x'] + box['width']}"
        )
