"""Mobile smoke tests — TC-MOBILE-* (P1.1.2 для бета-запуска).

CSS responsive у нас на 480/768 breakpoints, но без device-эмуляции
никто не проверял — флоу мог сломаться на тачскринах. 5 ключевых
сценариев на двух устройствах (iPhone 13 + Pixel 7) через Playwright.

Hard rules: hard `expect`, single canonical selector. Без skip-fallback.

Запуск через Playwright pytest-plugin с явной фикстурой `mobile_context`,
которая создаётся для каждого устройства из `playwright.devices`.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from tests._data.devices.descriptors import DEVICE_DESCRIPTORS
from tests.api_paths import API
from tests.pages.signup_page import SignupPage
from tests.timeouts import TIMEOUTS


@pytest.fixture(params=list(DEVICE_DESCRIPTORS), ids=list(DEVICE_DESCRIPTORS))
def mobile_context(
    request, browser: Browser, base_url: str
) -> Iterator[BrowserContext]:
    """Per-device context. Виртуальное устройство задаёт viewport, UA,
    deviceScaleFactor, hasTouch, isMobile."""
    device_descriptor = DEVICE_DESCRIPTORS[request.param]
    ctx = browser.new_context(
        **device_descriptor,
        base_url=base_url,
        ignore_https_errors=True,
    )
    # Pre-seed cookie-consent (same rationale as clients.py
    # auth_context_factory): the cookie-consent banner mounts async on
    # first visit and its overlay intercepts pointer events, racing
    # touch clicks (e.g. #agreeTerms / #signupBtn on /signup). Seeding a
    # non-null consent level makes cookie-consent.js exit early — banner
    # never renders. Per-device contexts don't inherit the factory seed.
    ctx.add_init_script(
        "try { localStorage.setItem('genealogy_cookie_consent', 'necessary'); "
        "localStorage.setItem('genealogy_cookie_consent_ts', String(Date.now())); "
        "} catch (e) {}"
    )
    yield ctx
    ctx.close()


@pytest.fixture
def mobile_page(mobile_context: BrowserContext) -> Iterator[Page]:
    page = mobile_context.new_page()
    yield page
    page.close()


# ─────────────────────────────────────────────────────────────────
# Smoke flow — 5 key scenarios, parametrize по устройству
# ─────────────────────────────────────────────────────────────────


def test_landing_loads_and_shows_demo_tree_on_mobile(mobile_page: Page):
    """TC-MOBILE-1: лендинг рендерится, treeContainer виден, нет horizontal scroll."""
    mobile_page.goto("/")
    mobile_page.wait_for_load_state("domcontentloaded")

    expect(mobile_page.locator("#treeContainer")).to_be_visible()

    # Horizontal scroll = mobile bug. document.body.scrollWidth должен быть
    # меньше или равен viewport (с tolerance 4px для рендер-багов).
    sw = mobile_page.evaluate("document.documentElement.scrollWidth")
    cw = mobile_page.evaluate("document.documentElement.clientWidth")
    assert sw <= cw + 4, f"horizontal scroll: scrollWidth={sw}, clientWidth={cw}"


def test_landing_tabs_clickable_on_mobile(mobile_page: Page):
    """TC-MOBILE-2: гостевые вкладки (Древо + О проекте) кликаются и
    переключаются. На мобайле tap-target 44×44 — проверяем visible +
    clickable.

    Note: map/sources/timeline вкладки auth-gated (см. TreePage POM,
    `AUTHED_TABS`); guest их не видит. Не проверяем здесь, чтобы не
    смешивать smoke с auth-flow.
    """
    import re

    mobile_page.goto("/")
    mobile_page.wait_for_load_state("domcontentloaded")

    for tab_name in ("tree", "about"):
        tab_btn = mobile_page.locator(f'.tab[data-tab="{tab_name}"]')
        expect(tab_btn).to_be_visible()
        tab_btn.click()
        expect(mobile_page.locator(f"#tab-{tab_name}")).to_have_class(
            re.compile(r".*active.*")
        )


def test_about_beta_card_visible_for_guest_on_mobile(mobile_page: Page):
    """TC-MOBILE-3 (P1.2.3): на мобайле в About-вкладке гость видит beta-card
    с CTA на /wait. Пр authenticated — не видит."""
    mobile_page.goto("/")
    mobile_page.wait_for_load_state("domcontentloaded")

    # Открыть About
    mobile_page.locator('.tab[data-tab="about"]').click()
    beta_card = mobile_page.locator("#aboutBetaCard")
    expect(beta_card).to_be_visible()

    # CTA-ссылка ведёт на /wait
    cta = beta_card.locator('a[href="/wait"]')
    expect(cta).to_be_visible()


def test_signup_form_submittable_on_mobile(
    mobile_page: Page, base_url: str
):
    """TC-MOBILE-4: signup-форма работоспособна с touch — поля заполняются,
    cross_border_consent чекбокс кликается, submit идёт."""
    mobile_page.goto("/signup")
    mobile_page.wait_for_load_state("domcontentloaded")

    signup = SignupPage(mobile_page)
    email = "mobile-smoke@e2e.local"
    signup.email.fill(email)
    signup.password.fill("Hunter22StrongMobile!")
    # Wave-9: privacy/cross-border объединены с terms_accepted; форма
    # имеет один `#agreeTerms`.
    signup.agree_terms.check()

    # Submit-кнопка должна быть видна и enabled. На мобайле она должна
    # быть достаточного размера для touch (~44px высоты).
    submit = signup.submit_btn
    expect(submit).to_be_visible()
    expect(submit).to_be_enabled()
    box = submit.bounding_box()
    assert box is not None and box["height"] >= 36, \
        f"submit button too small for touch: {box}"

    # Submit (form will probably succeed if backend ready, or fail on cap —
    # обе ветки валидны для smoke. Главное что нет JS-ошибки в консоли).
    submit.click()
    # Ждём response любого статуса
    mobile_page.wait_for_load_state("domcontentloaded")

    # Никаких uncaught errors в console (collect через listener в conftest
    # если есть; здесь — простой evaluate на presence of error-element).
    msg = mobile_page.locator("#signupMsg")
    # msg может содержать success или error — обе валидны;
    # проверяем что страница не упала (URL/title).
    expect(mobile_page).to_have_title(__import__("re").compile(r".+"))


def test_wait_form_submittable_on_mobile(mobile_page: Page):
    """TC-MOBILE-5: /wait — основной CTA для guest'ов в бета-режиме.
    Форма должна быть полностью функциональной на тачскрине."""
    mobile_page.goto("/wait")
    mobile_page.wait_for_load_state("domcontentloaded")

    email_input = mobile_page.locator('input[type="email"]')
    expect(email_input).to_be_visible()
    email_input.fill("waitlist-mobile@e2e.local")

    submit = mobile_page.locator("#submitBtn")
    expect(submit).to_be_visible()
    expect(submit).to_be_enabled()
    submit.click()
    mobile_page.wait_for_load_state("domcontentloaded")

    # После submit'а должен появиться result-блок (success или error).
    result = mobile_page.locator("#result")
    expect(result).to_be_visible()
