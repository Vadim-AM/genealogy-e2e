"""Admin (/admin) — legacy admin password login + people/sources/diagnostics tabs.

Aligned with docs/E2E_TEST_LOG.md (manual run 2026-04-23) sections 1-6.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.pages.admin_page import AdminPage


def test_admin_login_form_visible_when_anonymous(page: Page):
    """E2E_TEST_LOG §1: /admin without auth → login form."""
    AdminPage(page).goto().expect_login_form()


def test_admin_login_with_wrong_password_shows_error(page: Page):
    """E2E_TEST_LOG §1.1: wrong password → #loginError becomes visible."""
    admin = AdminPage(page).goto()
    admin.login("wrong_admin_password")
    expect(admin.login_error).to_be_visible()


def test_admin_login_with_correct_password_authenticates(page: Page):
    """E2E_TEST_LOG §1.2: correct password → admin panel renders, login form gone."""
    admin = AdminPage(page).goto()
    admin.login("test_admin_password")
    expect(admin.tab_people).to_be_visible()
    expect(admin.login_section).not_to_be_visible()


def test_admin_tabs_visible_after_auth(page: Page):
    """E2E_TEST_LOG §2-6: people/relationships/sources/diagnostics tabs all visible."""
    admin = AdminPage(page).goto()
    admin.login("test_admin_password")
    expect(admin.tab_people).to_be_visible()
    expect(admin.tab_relationships).to_be_visible()
    expect(admin.tab_sources).to_be_visible()
    expect(admin.tab_diagnostics).to_be_visible()
