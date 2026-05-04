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

import json
import re

from playwright.sync_api import Page, expect, Route

from tests.constants import unique_email


_PASSWORD = "test_password_8plus"
_IS_OPEN = re.compile(r"\bis-open\b")


def _mock_signup_overflow(page: Page, *, email: str, subscribed: bool = True) -> None:
    """Перехватить POST /api/account/signup и вернуть waitlist_required.

    Frontend (signup.html:515) смотрит на `j.status === 'waitlist_required'`
    → openWaitlistModal({email, subscribed: !!j.waitlist_subscribed}).
    """

    def handler(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "status": "waitlist_required",
                "email": email,
                "waitlist_subscribed": subscribed,
            }),
        )

    page.route("**/api/account/signup", handler)


def _fill_and_submit(page: Page, email: str) -> None:
    page.locator("#email").fill(email)
    page.locator("#password").fill(_PASSWORD)
    page.locator("#agreeTerms").check()
    page.locator("#agreePrivacy").check()
    page.locator("#agreeCrossBorder").check()
    page.locator("#signupBtn").click()


def test_waitlist_modal_opens_with_user_email_on_overflow_response(page: Page):
    """TC-22.04 (open): backend → waitlist_required → модалка открывается,
    title «Сейчас принимаем не всех», email юзера встроен в #waitlistBody2.

    Note: signup.html:396 перезаписывает innerHTML #waitlistBody2 на текст
    «Записали <strong>{email}</strong> в список ожидания…» — статический
    `<strong id="waitlistEmail">` из исходного HTML при этом исчезает.
    Поэтому assert через текст body2, а не через #waitlistEmail.
    """
    test_email = unique_email("overflow-modal")
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    _mock_signup_overflow(page, email=test_email)
    _fill_and_submit(page, test_email)

    overlay = page.locator("#waitlistOverlay")
    expect(overlay).to_have_class(_IS_OPEN)
    expect(page.locator("#waitlistTitle")).to_contain_text("Сейчас принимаем не всех")
    expect(page.locator("#waitlistBody2")).to_contain_text(test_email)
    expect(page.locator("#waitlistBody2")).to_contain_text("список ожидания")


def test_waitlist_modal_ok_button_redirects_to_landing(page: Page):
    """TC-22.04 (close-ok): click «Понятно» → закрывает модалку и
    делает redirect на / (signup.html:407: location.href = '/').
    """
    test_email = unique_email("overflow-ok")
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    _mock_signup_overflow(page, email=test_email)
    _fill_and_submit(page, test_email)

    expect(page.locator("#waitlistOverlay")).to_have_class(_IS_OPEN)
    page.locator("#waitlistOk").click()
    page.wait_for_url(re.compile(r"/$"))


def test_waitlist_modal_esc_closes_without_redirect(page: Page):
    """TC-22.05: Esc убирает класс .is-open, но НЕ делает redirect —
    юзер остаётся на /signup. Это сознательное решение (signup.html:411):
    не блокируем юзера если он промахнулся клавишей.
    """
    test_email = unique_email("overflow-esc")
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    _mock_signup_overflow(page, email=test_email)
    _fill_and_submit(page, test_email)

    overlay = page.locator("#waitlistOverlay")
    expect(overlay).to_have_class(_IS_OPEN)

    page.keyboard.press("Escape")
    expect(overlay).not_to_have_class(_IS_OPEN)
    assert page.url.rstrip("/").endswith("/signup"), (
        f"Esc должен закрыть модалку без redirect, но URL стал {page.url!r}"
    )


def test_waitlist_modal_shows_wait_link_when_auto_subscribe_failed(page: Page):
    """TC-22.04 (fallback): когда backend не смог auto-subscribe
    (waitlist_subscribed=false), модалка показывает CTA на /wait
    для повторной подписки вручную (signup.html:399).
    """
    test_email = unique_email("overflow-fallback")
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    _mock_signup_overflow(page, email=test_email, subscribed=False)
    _fill_and_submit(page, test_email)

    expect(page.locator("#waitlistOverlay")).to_have_class(_IS_OPEN)
    fallback_link = page.locator('#waitlistBody2 a[href*="/wait"]')
    expect(fallback_link).to_be_visible()
