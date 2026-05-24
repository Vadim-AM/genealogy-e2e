"""Pricing UI — TC-N1, TC-N2 (Phase D rollout, май 2026)."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.pricing_page import PricingPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory

@allure.title("Тарифы API: /api/tiers/public возвращает 4 тарифа")
def test_public_tiers_endpoint_returns_four_paid_tiers(uvicorn_server: str) -> None:
    """TC-N2: GET /api/tiers/public должен отдавать 4 publik-тарифа в ₽."""
    with step("действие: запросить /api/tiers/public"):
        r = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}")
        expect_response(r, label="GET /api/tiers/public").status(HTTPStatus.OK)
        body = r.json()

    with step("проверка: 4 публичных тарифа без служебных"):
        should.be_false(body.get("hidden"), ErrMsg.tiers_hidden_wrong)
        items = body["items"]
        names = {i["tier_name"] for i in items}

        expected = {"free", "starter", "researcher", "pro"}
        missing = expected - names
        should.be_empty(missing, ErrMsg.tier_missing)

        # b2b / self_hosted / beta — служебные, не должны показываться публично
        forbidden = {"b2b", "self_hosted", "beta"} & names
        should.be_empty(forbidden, ErrMsg.forbidden_tier_visible)


@allure.title("Тарифы API: у каждого тарифа есть название и цена в ₽")
def test_public_tiers_have_display_name_and_numeric_prices(uvicorn_server: str) -> None:
    """TC-N1: каждый тариф имеет непустой `display_name` и числовые цены."""
    with step("действие: запросить тарифы"):
        body = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}").json()
        by_name = {i["tier_name"]: i for i in body["items"]}

    with step("проверка: display_name и цены корректны"):
        for tier in ("free", "starter", "researcher", "pro"):
            t = by_name[tier]
            has_display_name = isinstance(t.get("display_name"), str) and t["display_name"].strip()
            should.be_true(has_display_name, ErrMsg.display_name_invalid)
            pm = t.get("price_rub_month")
            py = t.get("price_rub_year")
            should.be_true(isinstance(pm, int) and pm >= 0, ErrMsg.price_invalid)
            should.be_true(isinstance(py, int) and py >= 0, ErrMsg.price_invalid)
            # Год либо равен 12× месяца (без скидки), либо больше нуля и >= месячной
            # стоимости. Для free (0/0) обе цены легитимно нулевые.
            if pm > 0:
                should.greater_or_equal(py, pm, ErrMsg.year_less_than_month)

    with step("проверка: free тариф нулевой"):
        should.be_equal(by_name["free"]["price_rub_month"], 0, ErrMsg.free_tier_not_zero)


@allure.title("Тарифы API: тарифы отсортированы по возрастанию цены")
def test_public_tiers_sorted_by_price_ascending(uvicorn_server: str) -> None:
    """TC-N1: тарифы отсортированы по цене (free → pro)."""
    body = httpx.get(f"{uvicorn_server}{routes.TIERS_PUBLIC}").json()
    prices = [i["price_rub_month"] for i in body["items"]]
    should.be_equal(prices, sorted(prices), ErrMsg.tiers_not_sorted)


@allure.title("Тарифы: страница /pricing.html загружается как HTML")
def test_pricing_page_loads_html(page: Page) -> None:
    """TC-N1: GET /pricing.html → 200 + text/html."""
    with step("действие: загрузить /pricing.html"):
        r = page.goto("/pricing.html")
        should.not_none(r, ErrMsg.page_navigation_failed)

    with step("проверка: 200 и content-type text/html"):
        should.be_equal(r.status, HTTPStatus.OK, ErrMsg.status_mismatch)
        ct = (r.headers.get("content-type") or "").lower()
        should.contain(ct, "text/html", ErrMsg.content_type_not_html)


@allure.title("Тарифы: на странице отображаются 4 карточки тарифов")
def test_pricing_renders_four_cards(anon_pages: PageFactory) -> None:
    """TC-N1: на /pricing рендерится 4 карточки (после JS-fetch в /api/tiers/public)."""
    pricing = anon_pages.navigate_to(PricingPage)
    pricing.expect_cards_visible()


@allure.title("Тарифы: каждая карточка имеет уникальный заголовок")
def test_pricing_cards_have_non_empty_headings(anon_pages: PageFactory) -> None:
    """TC-N1: каждая карточка имеет non-empty `<h2>` (название тарифа)."""
    with step("действие: загрузить страницу тарифов"):
        pricing = anon_pages.navigate_to(PricingPage)
        expect(pricing.cards().first, ErrMsg.pricing_card_not_visible).to_be_visible()

    with step("проверка: 4 уникальных непустых заголовка"):
        found = pricing.card_titles()
        should.have_length(found, 4, ErrMsg.count_mismatch)
        should.be_true(all(found), ErrMsg.display_name_invalid)
        should.have_length(set(found), 4, ErrMsg.display_name_invalid)


@allure.title("Тарифы: на странице присутствует символ рубля ₽")
def test_pricing_cards_show_rub_symbol(page: Page, anon_pages: PageFactory) -> None:
    """TC-N1: на странице должен быть символ ₽."""
    with step("действие: загрузить страницу тарифов"):
        pricing = anon_pages.navigate_to(PricingPage)
        expect(pricing.cards().first, ErrMsg.pricing_card_not_visible).to_be_visible()

    with step("проверка: символ ₽ присутствует"):
        body_html = page.content()
        should.contain(body_html, "₽", ErrMsg.rub_symbol_missing)


@allure.title("Тарифы: карточка Исследователь выделена как featured")
def test_pricing_researcher_card_is_featured_by_position(
    page: Page, uvicorn_server: str, anon_pages: PageFactory,
) -> None:
    """TC-N1: featured-карточка (CSS-класс `.featured`) соответствует."""
    with step("подготовка: определить позицию researcher в API"):
        body = httpx.get(
            f"{uvicorn_server}{routes.TIERS_PUBLIC}"
        ).json()
        items = body["items"]
        researcher_idx = next(
            (i for i, t in enumerate(items) if t["tier_name"] == "researcher"),
            None,
        )
        should.not_none(researcher_idx, ErrMsg.tier_missing)

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
def test_pricing_no_console_errors(page: Page, anon_pages: PageFactory) -> None:
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
        should.be_empty(real, ErrMsg.js_errors_on_page)


# NB: setup требует superadmin auth + PATCH /api/platform/settings, что
# триггерит BUG-012 (per-email rate-limit на superadmin signup в genealogy/
# docs/test-cases/bugs.md). Тест осознанно НЕ написан — добавится после
# BUG-012 fix. Не использую pytest.skip-фикстуру: пустой test = false safety
# по правилам CLAUDE.md в этом репо. Лучше отсутствие, чем pass-by-default.
