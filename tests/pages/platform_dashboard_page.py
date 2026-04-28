"""POM for /platform/dashboard — superadmin metrics."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class PlatformDashboardPage(BasePage):
    URL = "/platform/dashboard"

    def __init__(self, page: Page):
        super().__init__(page)
        self.m_tenants = page.locator("#m_tenants")
        self.m_signups = page.locator("#m_signups")
        self.m_signups_7 = page.locator("#m_signups7")
        self.m_signups_30 = page.locator("#m_signups30")
        self.m_subs = page.locator("#m_subs")
        self.m_cap = page.locator("#m_cap")
        self.funnel = page.locator("#funnel")
        self.tenants_table = page.locator("#tenants_table")
        self.acq_signup_table = page.locator("#acq_signup_table")
        self.acq_waitlist_table = page.locator("#acq_waitlist_table")
        self.grant_email = page.locator("#grant_email")
        self.grant_btn = page.locator("#grant_btn")
        self.grant_msg = page.locator("#grant_msg")

    def grant_free_license(self, email: str) -> "PlatformDashboardPage":
        self.grant_email.fill(email)
        self.grant_btn.click()
        return self

    def soft_check_metrics_loaded(self, soft) -> None:
        for loc in (self.m_tenants, self.m_signups, self.tenants_table):
            soft(loc).to_be_visible()
