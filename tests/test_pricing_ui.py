"""Pricing UI — TC-N1, TC-N2 (Phase D rollout, май 2026).

Public pricing page рендерит карточки тарифов с **русскими названиями** и
**ценами в ₽**. Источник истины — `GET /api/tiers/public` (динамический
endpoint, не статический HTML). Управляется через `TierConfig` в БД +
`PlatformSettings.hide_pricing_ui` toggle.

Ожидаемое поведение (по Phase D):
- 4 публичных тарифа: Свободный (0 ₽), Стартовый (290), Исследователь (690),
  Профессионал (1490 ₽/мес)
- Featured карточка — researcher (имеет .featured CSS-класс)
- b2b / self_hosted / beta — НЕ показываются на публичной странице
- Сортировка по цене ↑
- При `hide_pricing_ui=true` (бета-режим) — карточки скрыты, показано
  объявление «Тарифы откроются в публичной бете»

Backend endpoints, на которые опираются эти тесты:
- `GET /pricing.html` — статика, доступна без auth
- `GET /api/tiers/public` — JSON, public
- `POST /api/_test/reset` (через autouse фикстуру) — чистит БД между тестами,
  пере-сидирует tier_config дефолтами из migration_seed.py
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API


# ─────────────────────────────────────────────────────────────────────────
# API-уровень — fast guards (без браузера)
# ─────────────────────────────────────────────────────────────────────────


def test_public_tiers_endpoint_returns_four_paid_tiers(uvicorn_server: str):
    """TC-N2: GET /api/tiers/public должен отдавать 4 publik-тарифа в ₽."""
    r = httpx.get(f"{uvicorn_server}/api/tiers/public", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body.get("hidden") is False, "Default hide_pricing_ui=False — items должны быть"
    items = body["items"]
    names = {i["tier_name"] for i in items}

    expected = {"free", "starter", "researcher", "pro"}
    missing = expected - names
    assert not missing, f"Не отдаются ожидаемые тарифы: {missing}; получили {names}"

    # b2b / self_hosted / beta — служебные, не должны показываться публично
    forbidden = {"b2b", "self_hosted", "beta"} & names
    assert not forbidden, f"На публичной странице утекли служебные тарифы: {forbidden}"


def test_public_tiers_have_ru_names_and_rub_prices(uvicorn_server: str):
    """TC-N1: каждый тариф имеет русское название + цену в ₽."""
    body = httpx.get(f"{uvicorn_server}/api/tiers/public", timeout=10).json()
    by_name = {i["tier_name"]: i for i in body["items"]}

    expected = {
        "free": ("Свободный", 0, 0),
        "starter": ("Стартовый", 290, 2900),
        "researcher": ("Исследователь", 690, 6900),
        "pro": ("Профессионал", 1490, 14900),
    }
    for tier, (ru_name, price_m, price_y) in expected.items():
        t = by_name[tier]
        assert t["display_name"] == ru_name, \
            f"{tier}: display_name = {t['display_name']!r}, ждали {ru_name!r}"
        assert t["price_rub_month"] == price_m, \
            f"{tier}: price_rub_month = {t['price_rub_month']}, ждали {price_m}"
        assert t["price_rub_year"] == price_y, \
            f"{tier}: price_rub_year = {t['price_rub_year']}, ждали {price_y}"


def test_public_tiers_sorted_by_price_ascending(uvicorn_server: str):
    """TC-N1: тарифы отсортированы по цене (free → pro)."""
    body = httpx.get(f"{uvicorn_server}/api/tiers/public", timeout=10).json()
    prices = [i["price_rub_month"] for i in body["items"]]
    assert prices == sorted(prices), \
        f"Тарифы не отсортированы по цене: {prices}"


# ─────────────────────────────────────────────────────────────────────────
# UI — реальный браузер на /pricing
# ─────────────────────────────────────────────────────────────────────────


def test_pricing_page_loads_html(page: Page):
    """TC-N1: GET /pricing.html → 200 + text/html."""
    r = page.goto("/pricing.html")
    assert r is not None
    assert r.status == 200
    ct = (r.headers.get("content-type") or "").lower()
    assert "text/html" in ct, f"content-type={ct!r}"


def test_pricing_renders_four_cards(page: Page):
    """TC-N1: на /pricing рендерится 4 карточки (после JS-fetch в /api/tiers/public).

    Если рендер не сработал — увидим .pricing-empty (скрыт по умолчанию).
    """
    page.goto("/pricing.html")
    page.wait_for_load_state("networkidle", timeout=10_000)

    # Ждём что карточки появились (динамический рендер из JS)
    page.wait_for_selector(".pricing-card", timeout=5_000)
    cards = page.locator(".pricing-card")
    assert cards.count() == 4, \
        f"Ожидали 4 карточки, получили {cards.count()}"


def test_pricing_cards_have_russian_names(page: Page):
    """TC-N1: каждая карточка содержит русское название тарифа."""
    page.goto("/pricing.html")
    page.wait_for_selector(".pricing-card", timeout=5_000)

    expected_names = {"Свободный", "Стартовый", "Исследователь", "Профессионал"}
    found_names = {h.inner_text().strip() for h in page.locator(".pricing-card h2").all()}
    missing = expected_names - found_names
    assert not missing, \
        f"На карточках не найдены названия: {missing}. Найдено: {found_names}"


def test_pricing_cards_show_rub_symbol(page: Page):
    """TC-N1: на странице должен быть символ ₽."""
    page.goto("/pricing.html")
    page.wait_for_selector(".pricing-card", timeout=5_000)
    body_html = page.content()
    assert "₽" in body_html, \
        "Символа ₽ нет в HTML — pricing форматирование сломано"


def test_pricing_researcher_is_featured(page: Page):
    """TC-N1: «Исследователь» подсвечен как featured (выделение CSS-классом)."""
    page.goto("/pricing.html")
    page.wait_for_selector(".pricing-card", timeout=5_000)

    featured = page.locator(".pricing-card.featured")
    assert featured.count() == 1, \
        f"Ожидали ровно 1 .featured карточку, получили {featured.count()}"
    h2 = featured.locator("h2").inner_text().strip()
    assert h2 == "Исследователь", \
        f"Featured карточка должна быть «Исследователь», получили {h2!r}"


def test_pricing_no_console_errors(page: Page):
    """TC-N1: на /pricing не должно быть JS exceptions."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.goto("/pricing.html")
    page.wait_for_load_state("networkidle", timeout=10_000)

    # Filter known noise (favicon 404 etc.)
    real = [e for e in errors if "favicon" not in e.lower()]
    assert not real, f"Console errors на /pricing: {real}"


# ─────────────────────────────────────────────────────────────────────────
# hide_pricing_ui mode — бета-режим (карточки скрыты)
# ─────────────────────────────────────────────────────────────────────────
# NB: setup требует superadmin auth + PATCH /api/platform/settings, что
# триггерит BUG-012 (per-email rate-limit на superadmin signup в genealogy/
# docs/test-cases/bugs.md). Тест осознанно НЕ написан — добавится после
# BUG-012 fix. Не использую pytest.skip-фикстуру: пустой test = false safety
# по правилам CLAUDE.md в этом репо. Лучше отсутствие, чем pass-by-default.
