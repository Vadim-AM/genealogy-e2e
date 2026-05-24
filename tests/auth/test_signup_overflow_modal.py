"""TC-22.04, TC-22.05 — Signup overflow → waitlist modal flow (UI-isolated).

Backend уже имеет тест на API-контракт overflow (`test_waitlist.py::
test_signup_overflow_returns_waitlist_required` + backend
`test_beta_signup_limit.py`). Здесь проверяется именно UI: при ответе
`{status: "waitlist_required", waitlist_subscribed: true}` от API
модалка `#waitlistOverlay` (signup.html:333) корректно открывается,
закрывается через «Понятно» с redirect на /, или Esc без redirect.

Backend response мочим через `page.route()` — это изолирует UI-тест
от текущей платформенной настройки `beta_user_cap` / env-override
`FREE_SIGNUP_LIMIT`. Если бы тест зависел от реального overflow flow,
ему пришлось бы создать N+1 signup'ов до cap'а либо мутировать
os.environ через дополнительный test endpoint.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from config.constants import unique_email
from framework.step import step
from helpers.auth.signup_helpers import fill_and_submit, mock_signup_overflow
from pages.signup_page import SignupPage
from src.texts import ErrMsg, Waitlist, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory

_IS_OPEN = re.compile(r"\bis-open\b")


@allure.title("Модалка листа ожидания открывается с email пользователя")
def test_waitlist_modal_opens_with_user_email_on_overflow_response(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (open): backend → waitlist_required → модалка открывается,
    title «Сейчас принимаем не всех», email юзера встроен в #waitlistBody2.

    Note: signup.html:396 перезаписывает innerHTML #waitlistBody2 на текст
    «Записали <strong>{email}</strong> в список ожидания…» — статический
    `<strong id="waitlistEmail">` из исходного HTML при этом исчезает.
    Поэтому assert через текст body2, а не через #waitlistEmail.
    """
    with step("подготовка: мок overflow response и submit формы"):
        test_email = unique_email("overflow-modal")
        _ = anon_pages.navigate_to(SignupPage)
        mock_signup_overflow(page, email=test_email)
        fill_and_submit(page, test_email)

    with step("проверка: модалка открылась с email и правильным title"):
        overlay = page.locator("#waitlistOverlay")
        expect(overlay, ErrMsg.wrong_css_class).to_have_class(_IS_OPEN)
        expect(page.locator("#waitlistTitle"), ErrMsg.wrong_text_content).to_contain_text(t(Waitlist.OVERFLOW_TITLE))
        expect(page.locator("#waitlistBody2"), ErrMsg.wrong_text_content).to_contain_text(test_email)
        expect(page.locator("#waitlistBody2"), ErrMsg.wrong_text_content).to_contain_text(t(Waitlist.WAITLIST_KEYWORD))


@allure.title("Кнопка 'Понятно' в модалке ожидания ведёт на главную")
def test_waitlist_modal_ok_button_redirects_to_landing(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (close-ok): click «Понятно» → закрывает модалку и
    делает redirect на / (signup.html:407: location.href = '/').
    """
    with step("подготовка: вызов overflow модалки"):
        test_email = unique_email("overflow-ok")
        _ = anon_pages.navigate_to(SignupPage)
        mock_signup_overflow(page, email=test_email)
        fill_and_submit(page, test_email)

    with step("действие: клик 'Понятно' и проверка redirect"):
        expect(page.locator("#waitlistOverlay"), ErrMsg.wrong_css_class).to_have_class(_IS_OPEN)
        page.locator("#waitlistOk").click()
        page.wait_for_url(re.compile(r"/$"))


@allure.title("Esc закрывает модалку ожидания без перенаправления")
def test_waitlist_modal_esc_closes_without_redirect(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.05: Esc убирает класс .is-open, но НЕ делает redirect —
    юзер остаётся на /signup. Это сознательное решение (signup.html:411):
    не блокируем юзера если он промахнулся клавишей.
    """
    with step("подготовка: вызов overflow модалки"):
        test_email = unique_email("overflow-esc")
        _ = anon_pages.navigate_to(SignupPage)
        mock_signup_overflow(page, email=test_email)
        fill_and_submit(page, test_email)

        overlay = page.locator("#waitlistOverlay")
        expect(overlay, ErrMsg.wrong_css_class).to_have_class(_IS_OPEN)

    with step("действие: нажатие Esc"):
        page.keyboard.press("Escape")

    with step("проверка: модалка закрылась, URL остался /signup"):
        expect(overlay, ErrMsg.overlay_should_be_closed).not_to_have_class(_IS_OPEN)
        assert page.url.rstrip("/").endswith("/signup"), (
            f"Esc должен закрыть модалку без redirect, но URL стал {page.url!r}"
        )


@allure.title("Модалка показывает ссылку /wait при неуспешной авто-подписке")
def test_waitlist_modal_shows_wait_link_when_auto_subscribe_failed(page: Page, anon_pages: PageFactory) -> None:
    """TC-22.04 (fallback): когда backend не смог auto-subscribe
    (waitlist_subscribed=false), модалка показывает CTA на /wait
    для повторной подписки вручную (signup.html:399).
    """
    with step("подготовка: вызов overflow модалки (subscribed=false)"):
        test_email = unique_email("overflow-fallback")
        _ = anon_pages.navigate_to(SignupPage)
        mock_signup_overflow(page, email=test_email, subscribed=False)
        fill_and_submit(page, test_email)

    with step("проверка: модалка показывает fallback-ссылку /wait"):
        expect(page.locator("#waitlistOverlay"), ErrMsg.wrong_css_class).to_have_class(_IS_OPEN)
        fallback_link = page.locator('#waitlistBody2 a[href*="/wait"]')
        expect(fallback_link, ErrMsg.link_not_visible).to_be_visible()
