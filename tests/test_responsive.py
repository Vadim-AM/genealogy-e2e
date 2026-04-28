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

from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from tests.messages import TestData


# ─────────────────────────────────────────────────────────────────────────
# Viewport-specific page fixtures
# ─────────────────────────────────────────────────────────────────────────


def _make_page(browser: Browser, base_url: str, *, w: int, h: int) -> Iterator[Page]:
    ctx: BrowserContext = browser.new_context(
        base_url=base_url,
        viewport={"width": w, "height": h},
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    yield page
    ctx.close()


@pytest.fixture
def mobile_page(browser: Browser, base_url: str) -> Iterator[Page]:
    """iPhone SE viewport — anonymous (no cookies)."""
    yield from _make_page(browser, base_url, w=375, h=812)


@pytest.fixture
def tablet_owner_page(
    browser: Browser, base_url: str, owner_user
) -> Iterator[Page]:
    """iPad portrait viewport with owner_user cookies + tenant header."""
    ctx = browser.new_context(
        base_url=base_url,
        viewport={"width": 768, "height": 1024},
        ignore_https_errors=True,
        extra_http_headers={"X-Tenant-Slug": owner_user.slug},
    )
    for name, value in owner_user.cookies.items():
        ctx.add_cookies([{"name": name, "value": value, "url": base_url}])
    ctx.add_init_script(
        "try { localStorage.setItem('v1', '1'); "
        "localStorage.setItem('genealogy_tour_v1', '1'); } catch (e) {}"
    )
    page = ctx.new_page()
    yield page
    ctx.close()


# ─────────────────────────────────────────────────────────────────────────
# 375×812 — iPhone SE
# ─────────────────────────────────────────────────────────────────────────


def test_signup_card_no_horizontal_scroll_on_iphone_se(mobile_page: Page):
    """TC-RESPONSIVE-1 (375): signup не вызывает горизонтальный скролл.

    Любое поле/кнопка, выходящее за viewport, ломает первое впечатление
    и conversion на мобильных (>50% трафика). Проверяем DOM-инвариант:
    documentElement.scrollWidth ≤ viewport.width.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("networkidle")

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


def test_signup_password_eye_toggle_visible_on_iphone_se(mobile_page: Page):
    """TC-RESPONSIVE-1 (375): #pwToggle (eye SVG) виден справа от поля пароля.

    На мобильных пользователю особенно важно видеть pw-toggle —
    клавиатура часто скрывает hint, а ошибка ввода без визуальной
    проверки бьёт по конверсии.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("networkidle")

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


def test_signup_consent_checkbox_label_does_not_overflow_on_iphone_se(
    mobile_page: Page,
):
    """TC-RESPONSIVE-1 (375): label чекбокса согласия не обрезается.

    Чекбокс `#agree` сидит в `.signup-agree` с label-текстом —
    при 375px текст должен переноситься, не выходить вправо.
    """
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("networkidle")

    agree_row = mobile_page.locator(".signup-agree")
    expect(agree_row).to_be_visible()
    box = agree_row.bounding_box()
    assert box is not None
    assert (box["x"] + box["width"]) <= 375, (
        f".signup-agree row overflows iPhone SE width: "
        f"right_edge={box['x'] + box['width']} > 375"
    )


# ─────────────────────────────────────────────────────────────────────────
# 768×1024 — iPad portrait
# ─────────────────────────────────────────────────────────────────────────


def test_all_five_tabs_visible_on_ipad_portrait(tablet_owner_page: Page, soft_check):
    """TC-RESPONSIVE-1 (768): все 5 главных tabs видны без обрезаний.

    Authenticated owner видит tree/map/sources/timeline/about. Если
    при portrait-режиме что-то схлопывается в hamburger — это уже
    другое UX-решение; на текущем макете все 5 должны быть на экране.
    """
    tablet_owner_page.goto("/")
    tablet_owner_page.wait_for_load_state("networkidle")

    for tab_name in ("tree", "map", "sources", "timeline", "about"):
        tab = tablet_owner_page.locator(f'[data-tab="{tab_name}"]')
        soft_check(tab).to_be_visible()
        box = tab.bounding_box()
        assert box is not None, f"tab {tab_name!r} not measurable"
        assert (box["x"] + box["width"]) <= 768, (
            f"tab {tab_name!r} overflows viewport at 768px: "
            f"right_edge={box['x'] + box['width']}"
        )
