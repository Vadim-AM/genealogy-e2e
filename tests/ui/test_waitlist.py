"""Waitlist (/wait) — F-WAIT-*, BUG-COPY-001 регрессия."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from assertions.base import should
from config.constants import unique_email
from framework.step import step
from pages.wait_page import WaitPage
from src.texts import PII, ErrMsg

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory


@allure.title("Вейтлист: форма подписки отображается на /wait")
def test_wait_page_renders_form(anon_pages: PageFactory) -> None:
    """F-WAIT-1: /wait → form visible."""
    wait = anon_pages.navigate_to(WaitPage)
    wait.expect_visible_form()


@allure.title("Вейтлист: отправка email успешно добавляет в очередь")
def test_wait_submit_email_success(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-2: submit → success message."""
    with step("действие: отправить email через waitlist"):
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r_info:
            wait.submit_email(unique_email("waitlist1"))

    with step("проверка: 200 и success-сообщение"):
        should.playwright_status(r_info.value, HTTPStatus.OK, ErrMsg.subscribe_status_wrong)
        wait.expect_success()


@allure.title("Вейтлист: на /wait нет персональных данных владельца")
def test_wait_no_owner_personal_data(page: Page, anon_pages: PageFactory) -> None:
    """BUG-COPY-001: /wait must not mention owner family names (PII)."""
    with step("действие: загрузить /wait"):
        _ = anon_pages.navigate_to(WaitPage)
        body = page.content()

    with step("проверка: нет PII владельца"):
        for needle in PII.OWNER_FAMILY_NAMES:
            should.not_contain(body, needle, ErrMsg.pii_leaked)


@allure.title("Вейтлист: невалидный email блокируется HTML5-проверкой")
def test_wait_submit_invalid_email_blocks_html5_validity(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-3: invalid email — input fails HTML5 validity (form does not submit)."""
    with step("действие: заполнить невалидный email и отправить"):
        wait = anon_pages.navigate_to(WaitPage)
        wait.email.fill("not-an-email")
        wait.submit_btn.click()

    with step("проверка: HTML5 validity false и result пуст"):
        is_valid = page.evaluate("() => document.getElementById('email').checkValidity()")
        should.be_false(is_valid, ErrMsg.html5_validity_passed)
        should.be_equal((wait.result.text_content() or "").strip(), "", ErrMsg.result_text_not_empty)


@allure.title("Вейтлист: повторная подписка возвращает already_subscribed")
def test_wait_duplicate_email_idempotent_status_field(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-4: re-submitting an already-subscribed email — idempotent contract."""
    with step("действие: первая подписка"):
        email = unique_email("dupe")
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r1_info:
            wait.submit_email(email)

    with step("проверка: первый submit -> status=ok"):
        r1 = r1_info.value
        should.playwright_status(r1, HTTPStatus.OK, ErrMsg.subscribe_status_wrong)
        body1 = r1.json()
        should.be_equal(body1.get("status"), "ok", ErrMsg.subscribe_status_wrong)
        wait.expect_success()

    with step("действие: повторная подписка тем же email"):
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r2_info:
            wait.submit_email(email)

    with step("проверка: дубликат -> status=already_subscribed"):
        r2 = r2_info.value
        should.playwright_status(r2, HTTPStatus.OK, ErrMsg.subscribe_status_wrong)
        body2 = r2.json()
        should.be_equal(body2.get("status"), "already_subscribed", ErrMsg.subscribe_status_wrong)
