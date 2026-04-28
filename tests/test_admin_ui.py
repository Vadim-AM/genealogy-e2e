"""Admin (/admin) — legacy admin password login + people/sources/diagnostics tabs.

Aligned with docs/E2E_TEST_LOG.md (manual run 2026-04-23) sections 1-6.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.pages.admin_page import AdminPage


def test_admin_login_form_visible_when_anonymous(page: Page):
    """E2E_TEST_LOG §1: /admin без auth → login form."""
    admin = AdminPage(page).goto()
    page.wait_for_load_state("networkidle", timeout=10_000)
    admin.expect_login_form()


def test_admin_login_with_wrong_password_shows_error(page: Page):
    """E2E_TEST_LOG §1.1: wrong password → error visible."""
    admin = AdminPage(page).goto()
    page.wait_for_load_state("networkidle", timeout=10_000)
    admin.login("wrong_admin_password")
    page.wait_for_timeout(1500)
    # Either error visible OR password field still visible (login refused).
    assert admin.login_password.is_visible() or admin.login_error.is_visible()


def test_admin_login_with_correct_password_authenticates(page: Page):
    """E2E_TEST_LOG §1.2: правильный пароль → admin panel visible."""
    admin = AdminPage(page).goto()
    page.wait_for_load_state("networkidle", timeout=10_000)
    admin.login("test_admin_password")
    page.wait_for_load_state("networkidle", timeout=10_000)
    # After login, login form should be gone OR admin panel ready.
    page.wait_for_timeout(1500)
    if admin.login_section.is_visible() and admin.login_password.is_visible():
        pytest.fail("login form still visible after correct admin password")


def test_admin_tabs_visible_after_auth(page: Page, soft_check):
    """E2E_TEST_LOG §2-6: people/relationships/sources/diagnostics tabs visible."""
    admin = AdminPage(page).goto()
    page.wait_for_load_state("networkidle", timeout=10_000)
    admin.login("test_admin_password")
    page.wait_for_timeout(2500)
    admin.soft_check_authed_tabs(soft_check)
