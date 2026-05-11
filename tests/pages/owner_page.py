"""POM for /owner — tenant owner dashboard."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class OwnerPage(BasePage):
    URL = "/owner"

    TABS = ["settings", "invites", "export", "subscription", "danger"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.tab_settings = page.locator('[data-tab="settings"]')
        self.tab_invites = page.locator('[data-tab="invites"]')
        self.tab_export = page.locator('[data-tab="export"]')
        self.tab_subscription = page.locator('[data-tab="subscription"]')
        self.tab_danger = page.locator('[data-tab="danger"]')

        # Settings tab inputs.
        self.cfg_site_name = page.locator("#cfg_site_name")
        self.cfg_family_name = page.locator("#cfg_family_name")
        self.cfg_regions = page.locator("#cfg_regions")
        self.cfg_contact_email = page.locator("#cfg_contact_email")
        self.cfg_about_text = page.locator("#cfg_about_text")
        self.cfg_save = page.locator("#cfgSave")

        # Invite tab locators are intentionally NOT pre-bound — the previous
        # `create_invite` helper used a 4-selector fallback chain to capture
        # the produced URL (CLAUDE.md rule #3 anti-pattern: "TODO, not a
        # passing test"). When the invite UI gets a stable `data-invite-url`
        # surface (Wave 2), re-add a tight helper here.

    def open_tab(self, name: str) -> "OwnerPage":
        self.page.locator(f'[data-tab="{name}"]').click()
        return self

    def update_settings(self, *, site_name: str | None = None) -> "OwnerPage":
        self.open_tab("settings")
        if site_name is not None:
            self.cfg_site_name.fill(site_name)
        self.cfg_save.click()
        return self

    def soft_check_all_tabs(self, soft) -> None:
        for tab in self.TABS:
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()
