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


def test_signup_short_password_sets_aria_invalid(page: Page):
    """A-SU-3: server returns 422 на short password → JS handler ставит
    `aria-invalid="true"` на password input.

    Используем server-side trigger (password too short), а не client-
    HTML5 (битый email): HTML5 native validity блокирует submit и
    JS handler не запускается, поэтому проверять aria-invalid на
    HTML5-fail бесполезно (даже после правильного фикса).

    P0.4 (ФЗ-156, май 2026): форма имеет 4 раздельных consent чекбокса
    вместо одного `#agree`. Поле `#full_name` удалено в commit 814d5f8 (I4).
    """
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    # Снимаем HTML5 ограничение minlength="8" на #password — иначе native
    # validity блокирует submit ДО fetch, JS error-handler не запускается,
    # тест проверяет уровень `aria-invalid` который ставится только из
    # response-handler. Server-side валидация (zxcvbn-python score>=2) —
    # источник истины, который мы и тестируем.
    page.evaluate("document.getElementById('password').removeAttribute('minlength')")
    page.locator("#email").fill("a11y-server@e2e.example.com")
    page.locator("#password").fill("short")  # < 8 chars — server rejects
    page.locator("#agreeTerms").check()
    page.locator("#agreePrivacy").check()
    page.locator("#agreeCrossBorder").check()

    # Wait for server response, then check aria state.
    with page.expect_response("**/api/account/signup") as resp_info:
        page.locator("#signupBtn").click()
    assert resp_info.value.status >= 400, (
        f"expected server validation error; got {resp_info.value.status}"
    )

    expect(page.locator("#password")).to_have_attribute(
        "aria-invalid", "true", timeout=TIMEOUTS.api_request * 1000
    )


def test_signup_honeypot_is_aria_hidden(page: Page):
    """A-SU-4: honeypot input has `aria-hidden="true"` (or its wrapper).

    Was xfail until upstream batch-6/7. Now regular regression.
    """
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    honeypot = page.locator("#website")
    expect(honeypot).to_have_attribute("aria-hidden", "true")
