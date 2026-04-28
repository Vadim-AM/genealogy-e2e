"""POM for /admin — tenant editor (legacy admin password OR auth_v2 owner)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class AdminPage(BasePage):
    URL = "/admin"

    def __init__(self, page: Page):
        super().__init__(page)
        # Login form: admin.html line 187-193
        self.login_section = page.locator("#loginSection")
        self.login_password = page.locator("#adminPassword")
        self.login_btn = page.locator("#loginSection button").first
        self.login_error = page.locator("#loginError")

        # Admin shell (admin.html line 196): #adminPanel
        self.admin_panel = page.locator("#adminPanel")
        self.tabs_container = page.locator(".admin-tabs")

        # Tabs use `data-admin-tab` attribute (NOT `data-tab` like the public site)
        self.tab_people = page.locator('.admin-tab[data-admin-tab="people"]')
        self.tab_relationships = page.locator('.admin-tab[data-admin-tab="relationships"]')
        self.tab_sources = page.locator('.admin-tab[data-admin-tab="sources-catalog"]')
        self.tab_diagnostics = page.locator('.admin-tab[data-admin-tab="diagnostics"]')
        self.tab_invites = page.locator('.admin-tab[data-admin-tab="invites"]')
        self.tab_analytics = page.locator('.admin-tab[data-admin-tab="analytics"]')

        # People list
        self.people_search = page.locator('input[placeholder*="оиск"], #peopleSearch').first
        self.person_rows = page.locator(".person-row, tr.person")

    def login(self, password: str) -> "AdminPage":
        self.login_password.fill(password)
        self.login_btn.click()
        return self

    def expect_login_form(self) -> None:
        expect(self.login_password).to_be_visible(timeout=5_000)

    def expect_authenticated(self) -> None:
        # Either admin panel visible, or some specific authed-only element
        expect(self.tab_people).to_be_visible(timeout=10_000)

    def open_tab(self, locator) -> "AdminPage":
        locator.click()
        return self

    def soft_check_authed_tabs(self, soft) -> None:
        for loc in (self.tab_people, self.tab_relationships, self.tab_sources, self.tab_diagnostics):
            soft(loc).to_be_visible()
