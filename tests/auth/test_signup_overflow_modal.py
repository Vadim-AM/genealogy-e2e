"""TC-22.04, TC-22.05 — Signup overflow → waitlist modal flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from config.constants import TestConfig, unique_email
from framework.step import step
from pages.signup_page import SignupPage
from pages.waitlist_modal import WaitlistModal
from src.texts import ErrMsg, Waitlist, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Модалка листа ожидания открывается с email пользователя")
def test_waitlist_modal_opens_with_user_email_on_overflow_response(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (open): overflow → модалка с title и email пользователя."""
    with step("подготовка: мок overflow response и submit формы"):
        test_email = unique_email("overflow-modal")
        _ = anon_pages.navigate_to(SignupPage)
        signup = SignupPage(page)
        signup.mock_overflow_response(email=test_email)
        signup.fill_required(email=test_email, password=TestConfig.DEFAULT_PASSWORD)
        signup.submit()

    with step("проверка: модалка открылась с email и правильным title"):
        modal = WaitlistModal(page)
        modal.expect_open()
        expect(modal.title, ErrMsg.wrong_text_content).to_contain_text(t(Waitlist.OVERFLOW_TITLE))
        expect(modal.body, ErrMsg.wrong_text_content).to_contain_text(test_email)
        expect(modal.body, ErrMsg.wrong_text_content).to_contain_text(
            t(Waitlist.WAITLIST_KEYWORD),
        )


@allure.title("Кнопка 'Понятно' в модалке ожидания ведёт на главную")
def test_waitlist_modal_ok_button_redirects_to_landing(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (close-ok): клик «Понятно» → redirect на /."""
    with step("подготовка: вызов overflow модалки"):
        test_email = unique_email("overflow-ok")
        _ = anon_pages.navigate_to(SignupPage)
        signup = SignupPage(page)
        signup.mock_overflow_response(email=test_email)
        signup.fill_required(email=test_email, password=TestConfig.DEFAULT_PASSWORD)
        signup.submit()

    with step("действие: клик 'Понятно' и проверка redirect"):
        modal = WaitlistModal(page)
        modal.expect_open()
        modal.click_ok()
        page.wait_for_url("**/")


@allure.title("Esc закрывает модалку ожидания без перенаправления")
def test_waitlist_modal_esc_closes_without_redirect(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.05: Esc закрывает модалку без redirect — URL остаётся /signup."""
    with step("подготовка: вызов overflow модалки"):
        test_email = unique_email("overflow-esc")
        _ = anon_pages.navigate_to(SignupPage)
        signup = SignupPage(page)
        signup.mock_overflow_response(email=test_email)
        signup.fill_required(email=test_email, password=TestConfig.DEFAULT_PASSWORD)
        signup.submit()

        modal = WaitlistModal(page)
        modal.expect_open()

    with step("действие: нажатие Esc"):
        modal.dismiss_via_escape()

    with step("проверка: модалка закрылась, URL остался /signup"):
        modal.expect_closed()
        should.be_true(page.url.rstrip("/").endswith("/signup"), ErrMsg.signup_url_not_preserved)


@allure.title("Модалка показывает ссылку /wait при неуспешной авто-подписке")
def test_waitlist_modal_shows_wait_link_when_auto_subscribe_failed(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (fallback): subscribed=false → модалка показывает ссылку /wait."""
    with step("подготовка: вызов overflow модалки (subscribed=false)"):
        test_email = unique_email("overflow-fallback")
        _ = anon_pages.navigate_to(SignupPage)
        signup = SignupPage(page)
        signup.mock_overflow_response(email=test_email, subscribed=False)
        signup.fill_required(email=test_email, password=TestConfig.DEFAULT_PASSWORD)
        signup.submit()

    with step("проверка: модалка показывает fallback-ссылку /wait"):
        modal = WaitlistModal(page)
        modal.expect_open()
        expect(modal.fallback_link(), ErrMsg.link_not_visible).to_be_visible()
