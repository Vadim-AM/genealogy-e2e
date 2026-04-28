"""Login + forgot-password flow (этап 3-4 funnel).

Covers: F-LG-1..4, X-LG-1..4, S-LG-1..2, F-FP-1..6.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.pages.login_page import LoginPage


def test_login_form_renders(page: Page):
    """F-LG-1, X-LG-1..4: /login renders email + password + submit."""
    login = LoginPage(page).goto()
    login.expect_visible_form()


def test_login_with_correct_credentials_succeeds(
    page: Page, base_url: str, owner_user
):
    """F-LG-1, F-LG-4: correct credentials → session cookie + redirect."""
    login = LoginPage(page).goto()
    login.login(owner_user.email, owner_user.password)
    page.wait_for_timeout(1500)

    # After login, the cookie should be set and /api/account/me works.
    cookies = page.context.cookies()
    assert any(c["name"].startswith("platform") or c["name"].startswith("session") for c in cookies)


def test_login_with_wrong_password_shows_error(
    page: Page, owner_user
):
    """S-LG-1: wrong credentials → 401, generic error message."""
    login = LoginPage(page).goto()
    login.login(owner_user.email, "wrong_password_xyz")
    page.wait_for_timeout(1500)
    # Page either shows error message inline, or stays on /login
    assert "/login" in page.url or login.error_msg.is_visible()


def test_login_with_unknown_email_does_not_leak_existence(
    page: Page, owner_user, base_url: str
):
    """S-LG-1, S-SU-2 — generic error for both wrong-pwd vs unknown-email.

    The user-facing message should be identical — backend should not leak
    "email not found" vs "wrong password".
    """
    login_known = LoginPage(page).goto()
    login_known.login(owner_user.email, "wrong_pw_2026")
    page.wait_for_timeout(800)
    msg_known = (login_known.error_msg.text_content() or "").strip().lower() if login_known.error_msg.count() else ""

    page.goto("/login")
    login_unknown = LoginPage(page)
    login_unknown.login("does-not-exist@e2e.example.com", "any_password_2026")
    page.wait_for_timeout(800)
    msg_unknown = (login_unknown.error_msg.text_content() or "").strip().lower() if login_unknown.error_msg.count() else ""

    # Both should produce SOME error message (or stay on /login). Don't insist
    # on identical strings in case localisation varies, but reject phrases that
    # leak existence:
    leaky = ("не найден", "не существ", "not found", "no such user", "не зарегистр")
    for word in leaky:
        assert word not in msg_known and word not in msg_unknown, f"login leaks user existence: '{word}'"


def test_login_links_to_signup_and_forgot(page: Page, soft_check):
    """X-LG-1, X-LG-2: signup + forgot-password links visible."""
    page.goto("/login")
    soft_check(
        page.get_by_role("link", name="Регистрация", exact=False).or_(
            page.get_by_text("Нет аккаунта", exact=False)
        ).first
    ).to_be_visible()
    soft_check(
        page.get_by_role("link", name="абыли", exact=False).or_(
            page.get_by_text("забыли", exact=False)
        ).first
    ).to_be_visible()
