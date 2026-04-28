"""TC-A11Y-1, TC-A11Y-2: accessibility regressions on signup form.

Two distinct fails for screen-reader users:

1. **BUG-A11Y-001** — при validation-error поле НЕ получает `aria-invalid="true"`
   и нет `aria-describedby` на error-msg. Скринридер не получает signal,
   что поле невалидно, пользователь не понимает почему submit не работает.

2. **BUG-A11Y-002** — honeypot `<input id="website">` имеет `tabindex="-1"`
   и скрыт визуально, но **не имеет `aria-hidden="true"`**. Скринридер
   честно прочитает поле «Сайт» и предложит заполнить. Пользователь со
   скринридером попадёт в ловушку: signup пройдёт «успешно» (200 silent),
   но user в БД не создан (honeypot triggered) — он ждёт письмо, которое
   никогда не придёт.

Тесты документируют контракт. Снять xfail когда продукт добавит
правильные ARIA-атрибуты.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.timeouts import TIMEOUTS


@pytest.mark.xfail(
    reason="BUG-A11Y-001: после server-side validation-fail на signup "
           "(short password) поле password не получает aria-invalid=\"true\" "
           "и нет aria-describedby на error-msg. Screen reader не получает "
           "signal что поле невалидно. Fix: в submit-handler signup.js, "
           "при server 422 — input.setAttribute('aria-invalid', 'true') + "
           "input.setAttribute('aria-describedby', '<field>-err').",
    strict=False,
)
def test_signup_short_password_sets_aria_invalid(page: Page):
    """A-SU-3: server returns 422 на short password → JS handler ставит
    `aria-invalid="true"` на password input.

    Используем server-side trigger (password too short), а не client-
    HTML5 (битый email): HTML5 native validity блокирует submit и
    JS handler не запускается, поэтому проверять aria-invalid на
    HTML5-fail бесполезно (даже после правильного фикса).
    """
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    # Email валидный для HTML5 (есть @), pass'ёт client validity →
    # submit реально отправляется → server-side rejection (short pw) →
    # JS error handler runs → должен пометить password aria-invalid.
    page.locator("#email").fill("a11y-server@e2e.example.com")
    page.locator("#password").fill("short")  # < 8 chars — server rejects
    page.locator("#full_name").fill("Test User")
    page.locator("#agree").check()

    # Wait for server response, then check aria state.
    with page.expect_response("**/api/account/signup") as resp_info:
        page.locator("#signupBtn").click()
    assert resp_info.value.status >= 400, (
        f"expected server validation error; got {resp_info.value.status}"
    )

    expect(page.locator("#password")).to_have_attribute(
        "aria-invalid", "true", timeout=TIMEOUTS.api_request * 1000
    )


@pytest.mark.xfail(
    reason="BUG-A11Y-002: honeypot `<input id=website>` имеет tabindex=-1, "
           "но не имеет aria-hidden=\"true\". Screen-reader читает поле "
           "«Сайт» и предлагает заполнить — пользователь попадает в "
           "ловушку, signup silently swallowed (200 без user). Fix: "
           "добавить `aria-hidden=\"true\"` на input#website в /signup, "
           "также на wrapper .signup-hp.",
    strict=False,
)
def test_signup_honeypot_is_aria_hidden(page: Page):
    """A-SU-4: honeypot input has `aria-hidden="true"` (or its wrapper)."""
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    honeypot = page.locator("#website")
    expect(honeypot).to_have_attribute("aria-hidden", "true")
