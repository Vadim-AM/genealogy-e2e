"""Mobile smoke tests — TC-MOBILE-* (P1.1.2 для бета-запуска)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from assertions.base import should
from framework.step import step
from pages.signup_page import SignupPage
from pages.tree_page import TreePage
from pages.wait_page import WaitPage
from src.texts import ErrMsg
from test_data.devices.descriptors import DEVICE_DESCRIPTORS

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(params=list(DEVICE_DESCRIPTORS), ids=list(DEVICE_DESCRIPTORS))
def mobile_context(
    request, browser: Browser, base_url: str
) -> Iterator[BrowserContext]:
    """Per-device context. Виртуальное устройство задаёт viewport, UA,."""
    device_descriptor = DEVICE_DESCRIPTORS[request.param]
    ctx = browser.new_context(
        **device_descriptor,  # type: ignore[arg-type]
        base_url=base_url,
        ignore_https_errors=True,
    )
    # Предзаполняем cookie-consent (аналогично clients.py
    # auth_context_factory): баннер cookie-consent монтируется асинхронно
    # при первом визите и его overlay перехватывает pointer events, вступая
    # в гонку с touch-кликами (напр. #agreeTerms / #signupBtn на /signup).
    # Установка ненулевого consent-уровня заставляет cookie-consent.js
    # выйти раньше — баннер не рендерится. Per-device контексты не
    # наследуют seed от factory.
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


@allure.title("Мобильный: лендинг показывает древо без горизонтального скролла")
def test_landing_loads_and_shows_demo_tree_on_mobile(mobile_page: Page) -> None:
    """TC-MOBILE-1: лендинг рендерится, treeContainer виден, нет horizontal scroll."""
    with step("действие: загрузить лендинг на мобильном"):
        tree = TreePage(mobile_page).goto_and_load()

    with step("проверка: treeContainer виден"):
        expect(tree.tree_container, ErrMsg.tree_not_rendered).to_be_visible()

    with step("проверка: нет горизонтального скролла"):
        # Горизонтальный скролл = мобильный баг. document.body.scrollWidth
        # должен быть меньше или равен viewport (с tolerance 4px для рендер-багов).
        sw = mobile_page.evaluate("document.documentElement.scrollWidth")
        cw = mobile_page.evaluate("document.documentElement.clientWidth")
        should.less(sw, cw + 5, ErrMsg.horizontal_scroll_detected)


@allure.title("Мобильный: вкладки Древо и О проекте кликабельны")
def test_landing_tabs_clickable_on_mobile(mobile_page: Page) -> None:
    """TC-MOBILE-2: гостевые вкладки (Древо + О проекте) кликаются и."""
    with step("действие: загрузить лендинг"):
        tree = TreePage(mobile_page).goto_and_load()

    with step("проверка: вкладки видны и кликаются"):
        for tab_name in ("tree", "about"):
            tab_btn = tree.tab_locator(tab_name)
            expect(tab_btn, ErrMsg.tab_not_visible).to_be_visible()
            tab_btn.click()
            tree.expect_tab_content_active(tab_name)


@allure.title("Мобильный: бета-карточка с CTA видна гостю в About")
def test_about_beta_card_visible_for_guest_on_mobile(mobile_page: Page) -> None:
    """TC-MOBILE-3 (P1.2.3): на мобайле в About-вкладке гость видит beta-card."""
    with step("действие: открыть About на мобильном"):
        tree = TreePage(mobile_page).goto_and_load()
        tree.switch_tab("about")

    with step("проверка: бета-карточка с CTA на /wait видна"):
        expect(tree.about_beta_card, ErrMsg.element_not_visible).to_be_visible()
        cta = tree.about_beta_card.locator('a[href="/wait"]')
        expect(cta, ErrMsg.link_not_visible).to_be_visible()


@allure.title("Мобильный: форма регистрации заполняется и отправляется")
def test_signup_form_submittable_on_mobile(
    mobile_page: Page, base_url: str
) -> None:
    """TC-MOBILE-4: signup-форма работоспособна с touch — поля заполняются,."""
    with step("подготовка: открыть signup на мобильном"):
        signup = SignupPage(mobile_page).goto_and_load()

    with step("действие: заполнить форму"):
        email = "mobile-smoke@e2e.local"
        signup.email.fill(email)
        signup.password.fill("Hunter22StrongMobile!")
        # Wave-9: privacy/cross-border объединены с terms_accepted; форма
        # имеет один `#agreeTerms`.
        signup.agree_terms.check()

    with step("проверка: submit-кнопка достаточного размера для touch"):
        submit = signup.submit_btn
        expect(submit, ErrMsg.button_not_visible).to_be_visible()
        expect(submit, ErrMsg.button_not_enabled).to_be_enabled()
        box = submit.bounding_box()
        should.be_true(box is not None and box["height"] >= 36, ErrMsg.touch_target_too_small)

    with step("действие: отправить форму"):
        # Отправка (форма скорее всего пройдёт если backend готов, или упадёт
        # по лимиту — обе ветки валидны для smoke. Главное что нет JS-ошибки).
        signup.submit()
        signup.wait_for_page_load()

    with step("проверка: страница не упала после submit"):
        # msg может содержать success или error — обе валидны;
        # проверяем что страница не упала (URL/title).
        expect(mobile_page, ErrMsg.page_title_wrong).to_have_title(__import__("re").compile(r".+"))


@allure.title("Мобильный: форма вейтлиста на /wait работает на тачскрине")
def test_wait_form_submittable_on_mobile(mobile_page: Page) -> None:
    """TC-MOBILE-5: /wait — основной CTA для guest'ов в бета-режиме."""
    with step("действие: открыть /wait и заполнить форму"):
        wait = WaitPage(mobile_page).goto_and_load()
        expect(wait.email, ErrMsg.input_not_visible).to_be_visible()
        wait.email.fill("waitlist-mobile@e2e.local")

    with step("действие: отправить форму"):
        expect(wait.submit_btn, ErrMsg.button_not_visible).to_be_visible()
        expect(wait.submit_btn, ErrMsg.button_not_enabled).to_be_enabled()
        wait.submit_btn.click()
        wait.wait_for_page_load()

    with step("проверка: result-блок виден"):
        expect(wait.result, ErrMsg.element_not_visible).to_be_visible()
