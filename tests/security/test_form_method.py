"""TC-FORM-1: public forms must POST credentials, never GET.

Без `method="post"` HTML5 default — GET → password / token попадают
в URL → история браузера → referer → access logs.

Тест проверяет **функциональный** контракт: при submit'е форма
действительно делает POST-запрос. Атрибут `method="post"` в DOM —
necessary, но не sufficient (JS может override'ить). Используем
`page.expect_request` чтобы поймать реальный submit и проверить
`request.method`.

Was xfail under BUG-FORM-001 until upstream commit `013d31f`. Now
plain regression.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

import allure

from tests.api_paths import API
from tests.constants import TestConfig, unique_email
from tests.messages import Buttons, t


def _is_submit_request(url: str, expected_path: str) -> bool:
    return expected_path in url


@allure.title("Формы: регистрация отправляется методом POST, не GET")
def test_signup_form_submits_via_post(page: Page):
    """Submit signup form → request method MUST be POST."""
    page.goto("/signup")
    page.wait_for_load_state("domcontentloaded")
    page.locator("#email").fill(unique_email("formpost"))
    page.locator("#password").fill(TestConfig.DEFAULT_PASSWORD)
    # Wave-9: privacy/cross-border объединены с terms_accepted (см. backend
    # router.py:417). В форме остался только `#agreeTerms`.
    page.locator("#agreeTerms").check()

    with page.expect_request(
        lambda req: _is_submit_request(req.url, API.SIGNUP)
    ) as req_info:
        page.locator("#signupBtn").click()
    assert req_info.value.method == "POST", (
        f"signup form submitted as {req_info.value.method}, expected POST. "
        f"Password leaks to URL/history if GET."
    )

    # DOM-уровневая sanity (на случай рефакторинга на FormData без fetch):
    expect(page.locator("#signupForm")).to_have_attribute("method", "post")


@allure.title("Формы: вход отправляется методом POST, не GET")
def test_login_form_submits_via_post(page: Page):
    """Submit login form → request method MUST be POST."""
    page.goto("/login")
    page.wait_for_load_state("domcontentloaded")
    page.locator("#email").fill(unique_email("formpost-li"))
    page.locator("#password").fill("any-password-here")

    with page.expect_request(
        lambda req: _is_submit_request(req.url, API.LOGIN)
    ) as req_info:
        page.get_by_role("button", name=t(Buttons.LOGIN), exact=False).click()
    assert req_info.value.method == "POST", (
        f"login form submitted as {req_info.value.method}, expected POST."
    )

    expect(page.locator("#loginForm")).to_have_attribute("method", "post")


@allure.title("Формы: сброс пароля имеет method=post")
def test_reset_password_form_method_is_post(page: Page):
    """Reset-password form structural check (method="post").

    Не submit'им реально (token fake → backend 4xx, network capture
    может zatajit'ся в timing); ограничиваемся структурным check'ом.
    """
    page.goto("/account/reset-password?token=fake-for-render")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#rpForm")).to_have_attribute("method", "post")
