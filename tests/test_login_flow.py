"""Login flow (этап 3 funnel).

Covers: F-LG-1..4, X-LG-1..4, S-LG-1..2.
"""

from __future__ import annotations

import re

import httpx

from tests.timeouts import TIMEOUTS
from playwright.sync_api import Page, expect

from tests.messages import Links, t
from tests.pages.login_page import LoginPage


def test_login_form_renders(page: Page):
    """F-LG-1, X-LG-1..4: /login renders email + password + submit."""
    login = LoginPage(page).goto()
    login.expect_visible_form()


def test_login_with_correct_credentials_succeeds(
    page: Page, base_url: str, owner_user
):
    """F-LG-1, F-LG-4: correct credentials → session cookie + /me returns tenant."""
    login = LoginPage(page).goto()

    with page.expect_response("**/api/account/login") as resp_info:
        login.login(owner_user.email, owner_user.password)
    assert resp_info.value.ok, f"login response not ok: {resp_info.value.status}"

    cookies = {c["name"]: c["value"] for c in page.context.cookies()}
    session_cookie = cookies.get("platform_session") or cookies.get("session_id")
    assert session_cookie, f"no platform_session/session_id cookie set after login: {cookies}"

    me = httpx.get(f"{base_url}/api/account/me", cookies=cookies, timeout=TIMEOUTS.api_request)
    me.raise_for_status()
    assert me.json()["tenant"]["slug"] == owner_user.slug


def test_login_with_wrong_password_shows_error(page: Page, owner_user):
    """S-LG-1: wrong credentials → visible inline error, no redirect away from /login."""
    login = LoginPage(page).goto()
    login.login(owner_user.email, "wrong_password_xyz")

    expect(login.error_msg).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login"))


def test_login_unknown_email_returns_same_error_as_wrong_password(
    page: Page, owner_user
):
    """S-LG-1, S-SU-2: unknown email vs wrong password — identical error text.

    No reverse-engineerable signal that an account does/does-not exist.
    """
    login = LoginPage(page).goto()
    login.login(owner_user.email, "wrong_pw_2026")
    expect(login.error_msg).to_be_visible()
    msg_known = login.error_msg.text_content()

    page.goto("/login")
    login_unknown = LoginPage(page)
    login_unknown.login("does-not-exist@e2e.example.com", "any_password_2026")
    expect(login_unknown.error_msg).to_be_visible()
    msg_unknown = login_unknown.error_msg.text_content()

    assert msg_known == msg_unknown, (
        f"login error texts differ — possible enumeration leak.\n"
        f"  known:   {msg_known!r}\n  unknown: {msg_unknown!r}"
    )


def test_login_links_to_signup_and_forgot(page: Page):
    """X-LG-1, X-LG-2: signup and forgot-password links visible on /login."""
    page.goto("/login")
    expect(page.get_by_role("link", name=t(Links.SIGNUP))).to_be_visible()
    expect(page.get_by_role("link", name=t(Links.FORGOT_PASSWORD))).to_be_visible()
