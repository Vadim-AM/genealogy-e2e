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

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from pages.pricing_page import PricingPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory

# ─────────────────────────────────────────────────────────────────────────
# API-уровень — fast guards (без браузера)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Тарифы API: /api/tiers/public возвращает 4 тарифа")
def test_public_tiers_endpoint_returns_four_paid_tiers(uvicorn_server: str):
    """TC-N2: GET /api/tiers/public должен отдавать 4 publik-тарифа в ₽."""
    with step("действие: запросить /api/tiers/public"):
        r = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}", timeout=TIMEOUTS.api_request)
        expect_response(r, label="GET /api/tiers/public").status(HTTPStatus.OK)
        body = r.json()

    with step("проверка: 4 публичных тарифа без служебных"):
        assert body.get("hidden") is False, "Default hide_pricing_ui=False — items должны быть"
        items = body["items"]
        names = {i["tier_name"] for i in items}

        expected = {"free", "starter", "researcher", "pro"}
        missing = expected - names
        assert not missing, f"Не отдаются ожидаемые тарифы: {missing}; получили {names}"

        # b2b / self_hosted / beta — служебные, не должны показываться публично
        forbidden = {"b2b", "self_hosted", "beta"} & names
        assert not forbidden, f"На публичной странице утекли служебные тарифы: {forbidden}"


@allure.title("Тарифы API: у каждого тарифа есть название и цена в ₽")
def test_public_tiers_have_display_name_and_numeric_prices(uvicorn_server: str):
    """TC-N1: каждый тариф имеет непустой `display_name` и числовые цены
    `price_rub_month` / `price_rub_year` (>= 0, год >= месяц).

    Локализационно-нейтрально: НЕ проверяем конкретный текст display_name
    (он меняется per-locale), только что поле заполнено и цены — корректные
    integer-значения.
    """
    with step("действие: запросить тарифы"):
        body = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}", timeout=TIMEOUTS.api_request).json()
        by_name = {i["tier_name"]: i for i in body["items"]}

    with step("проверка: display_name и цены корректны"):
        for tier in ("free", "starter", "researcher", "pro"):
            t = by_name[tier]
            assert isinstance(t.get("display_name"), str) and t["display_name"].strip(), (
                f"{tier}: display_name пуст или не string: {t.get('display_name')!r}"
            )
            pm = t.get("price_rub_month")
            py = t.get("price_rub_year")
            assert isinstance(pm, int) and pm >= 0, f"{tier}: invalid price_rub_month: {pm!r}"
            assert isinstance(py, int) and py >= 0, f"{tier}: invalid price_rub_year: {py!r}"
            # Год либо равен 12× месяца (без скидки), либо больше нуля и >= месячной
            # стоимости. Для free (0/0) обе цены легитимно нулевые.
            if pm > 0:
                assert py >= pm, f"{tier}: год ({py}) меньше месяца ({pm})"

    with step("проверка: free тариф нулевой"):
        assert by_name["free"]["price_rub_month"] == 0, (
            f"free tier must be 0 ₽; got {by_name['free']['price_rub_month']}"
        )


@allure.title("Тарифы API: тарифы отсортированы по возрастанию цены")
def test_public_tiers_sorted_by_price_ascending(uvicorn_server: str):
    """TC-N1: тарифы отсортированы по цене (free → pro)."""
    body = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}", timeout=TIMEOUTS.api_request).json()
    prices = [i["price_rub_month"] for i in body["items"]]
    assert prices == sorted(prices), \
        f"Тарифы не отсортированы по цене: {prices}"


# ─────────────────────────────────────────────────────────────────────────
# UI — реальный браузер на /pricing
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Тарифы: страница /pricing.html загружается как HTML")
def test_pricing_page_loads_html(page: Page):
    """TC-N1: GET /pricing.html → 200 + text/html."""
    with step("действие: загрузить /pricing.html"):
        r = page.goto("/pricing.html")
        assert r is not None, "page.goto returned None (navigation failed)"

    with step("проверка: 200 и content-type text/html"):
        assert r.status == HTTPStatus.OK, f"GET /pricing.html: expected 200, got {r.status}"
        ct = (r.headers.get("content-type") or "").lower()
        assert "text/html" in ct, f"content-type={ct!r}"


@allure.title("Тарифы: на странице отображаются 4 карточки тарифов")
def test_pricing_renders_four_cards(anon_pages: PageFactory):
    """TC-N1: на /pricing рендерится 4 карточки (после JS-fetch в /api/tiers/public).

    Если рендер не сработал — увидим .pricing-empty (скрыт по умолчанию).
    """
    pricing = anon_pages.navigate_to(PricingPage)
    pricing.expect_cards_visible()


@allure.title("Тарифы: каждая карточка имеет уникальный заголовок")
def test_pricing_cards_have_non_empty_headings(anon_pages: PageFactory):
    """TC-N1: каждая карточка имеет non-empty `<h2>` (название тарифа).

    Локализационно-нейтрально: проверяем что у всех 4 карточек есть
    заголовок и он не пустой; конкретный текст определяется backend
    `display_name`, который зависит от locale.
    """
    with step("действие: загрузить страницу тарифов"):
        pricing = anon_pages.navigate_to(PricingPage)
        expect(pricing.cards().first, ErrMsg.pricing_card_not_visible).to_be_visible()

    with step("проверка: 4 уникальных непустых заголовка"):
        found = pricing.card_titles()
        assert len(found) == 4, f"expected 4 card titles; got {len(found)}"
        assert all(found), f"Найдены пустые заголовки карточек: {found!r}"
        assert len(set(found)) == 4, (
            f"display_name на карточках должны быть уникальными; "
            f"получили дубли: {found!r}"
        )


@allure.title("Тарифы: на странице присутствует символ рубля ₽")
def test_pricing_cards_show_rub_symbol(page: Page, anon_pages: PageFactory):
    """TC-N1: на странице должен быть символ ₽."""
    with step("действие: загрузить страницу тарифов"):
        pricing = anon_pages.navigate_to(PricingPage)
        expect(pricing.cards().first, ErrMsg.pricing_card_not_visible).to_be_visible()

    with step("проверка: символ ₽ присутствует"):
        body_html = page.content()
        assert "₽" in body_html, \
            "Символа ₽ нет в HTML — pricing форматирование сломано"


@allure.title("Тарифы: карточка Исследователь выделена как featured")
def test_pricing_researcher_card_is_featured_by_position(
    page: Page, uvicorn_server: str, anon_pages: PageFactory,
):
    """TC-N1: featured-карточка (CSS-класс `.featured`) соответствует
    `researcher` tier из `/api/tiers/public`.

    Локализационно-нейтрально: связь UI ↔ tier-id определяется
    через position в backend-response — UI рендерит cards в том же
    порядке. `display_name` (текст) не используем.
    """
    with step("подготовка: определить позицию researcher в API"):
        body = httpx.get(
            f"{uvicorn_server}{routes.TIERS_PUBLIC}", timeout=TIMEOUTS.api_request
        ).json()
        items = body["items"]
        researcher_idx = next(
            (i for i, t in enumerate(items) if t["tier_name"] == "researcher"),
            None,
        )
        assert researcher_idx is not None, (
            f"researcher tier отсутствует в /api/tiers/public: {[t['tier_name'] for t in items]}"
        )

    with step("действие: загрузить страницу тарифов"):
        pricing = anon_pages.navigate_to(PricingPage)
        expect(pricing.cards().first, ErrMsg.pricing_card_not_visible).to_be_visible()
        pricing.expect_cards_visible(len(items))

    with step("проверка: researcher-карточка имеет класс featured"):
        expect(pricing.featured, ErrMsg.wrong_count).to_have_count(1)
        researcher_card = pricing.cards().nth(researcher_idx)
        # to_have_class matches the full class attribute string, поэтому
        # regex substring `\\bfeatured\\b`.
        expect(researcher_card, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bfeatured\b"))


@allure.title("Тарифы: нет JS-ошибок в консоли на /pricing")
def test_pricing_no_console_errors(page: Page, anon_pages: PageFactory):
    """TC-N1: на /pricing не должно быть JS exceptions."""
    with step("подготовка: подключить listeners на ошибки"):
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
        page.on(
            "console",
            lambda msg: errors.append(msg.text) if msg.type == "error" else None,
        )

    with step("действие: загрузить /pricing.html"):
        _ = anon_pages.navigate_to(PricingPage)

    with step("проверка: нет JS-ошибок в консоли"):
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
