"""TC-FORM-1: public forms must declare `method="post"`.

Без явного `method` атрибута HTML5 spec требует от браузера использовать
GET — т.е. password / token попадает в URL → история браузера →
referer-headers → access logs провайдеров → возможно reverse proxy logs.

Затрагивает три публичные формы:
- `/signup`            → password в query string при миссинге
- `/login`             → password в query string при миссинге
- `/account/reset-password` → новый пароль в query string

Run 2 (28.04) подтвердил все три без атрибута. Тест документирует
контракт. xfail снимется когда продукт-фикс добавит method="post".
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


_FORM_METHOD_XFAIL = pytest.mark.xfail(
    reason="BUG-FORM-001: <form> без method attribute → default GET в HTML5 → "
           "пароли/токены утекают в URL/history/referer/logs. Confirmed in "
           "Run 2 (28.04) for /signup, /login, /account/reset-password. Fix: "
           "add method=\"post\" to <form id=signupForm|loginForm|rpForm>.",
    strict=False,
)


@_FORM_METHOD_XFAIL
def test_signup_form_method_is_post(page: Page):
    """Signup form sends password — must POST, never GET."""
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#signupForm")).to_have_attribute("method", "post")


@_FORM_METHOD_XFAIL
def test_login_form_method_is_post(page: Page):
    """Login form sends password — must POST, never GET."""
    page.goto("/login")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#loginForm")).to_have_attribute("method", "post")


@_FORM_METHOD_XFAIL
def test_reset_password_form_method_is_post(page: Page):
    """Reset-password form sends new password — must POST, never GET."""
    page.goto("/account/reset-password?token=fake-token-just-for-render")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#rpForm")).to_have_attribute("method", "post")
