"""TC-FORM-1: public forms must declare `method="post"`.

Без явного `method` атрибута HTML5 spec требует от браузера использовать
GET — т.е. password / token попадает в URL → история браузера →
referer-headers → access logs провайдеров → возможно reverse proxy logs.

Was xfail under BUG-FORM-001 until upstream commit `013d31f`
("fix(forms): method=post на signup/login/forgot/reset"). Now plain
regression — keep all three forms POST forever.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_signup_form_method_is_post(page: Page):
    """Signup form sends password — must POST, never GET."""
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#signupForm")).to_have_attribute("method", "post")


def test_login_form_method_is_post(page: Page):
    """Login form sends password — must POST, never GET."""
    page.goto("/login")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#loginForm")).to_have_attribute("method", "post")


def test_reset_password_form_method_is_post(page: Page):
    """Reset-password form sends new password — must POST, never GET."""
    page.goto("/account/reset-password?token=fake-token-just-for-render")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#rpForm")).to_have_attribute("method", "post")
