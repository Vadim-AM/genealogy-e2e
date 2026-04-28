"""POM for / (index.html) — public family tree."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from .base import BasePage


class TreePage(BasePage):
    URL = "/"

    # Guests only see tree + about; map/sources/timeline are auth-gated.
    GUEST_TABS = ["tree", "about"]
    AUTHED_TABS = ["tree", "map", "sources", "timeline", "about"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.h1 = page.locator("h1").first
        self.tab_tree = page.locator('[data-tab="tree"]')
        self.tab_map = page.locator('[data-tab="map"]')
        self.tab_sources = page.locator('[data-tab="sources"]')
        self.tab_timeline = page.locator('[data-tab="timeline"]')
        self.tab_about = page.locator('[data-tab="about"]')
        self.search_input = page.locator("#personSearch")
        self.search_results = page.locator("#personSearchResults")
        self.tree_container = page.locator("#treeContainer")
        self.minimap = page.locator("#minimap")
        self.auth_indicator = page.locator("#authIndicator")
        self.tour_replay_btn = page.locator("#tourReplayBtn")

    def switch_to(self, tab_name: str) -> "TreePage":
        """tab_name: 'tree' | 'map' | 'sources' | 'timeline' | 'about'."""
        self.page.locator(f'[data-tab="{tab_name}"]').click()
        return self

    def expect_tree_rendered(self) -> None:
        """DEFERRED (Wave 2): currently only verifies the loading-indicator
        disappeared. That passes on an empty tree or a fallback "no data" UI.
        Replace with a concrete card-count assertion against the demo seed
        once the orbit-card selector is confirmed.
        """
        expect(self.tree_container).to_be_visible()
        expect(self.tree_container.locator(".loading-indicator")).not_to_be_visible()

    def search_person(self, query: str) -> "TreePage":
        self.search_input.fill(query)
        return self

    def soft_check_guest_tabs(self, soft) -> None:
        """Tabs visible to anonymous visitors (tree + about)."""
        for tab in self.GUEST_TABS:
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()

    def soft_check_authed_tabs(self, soft) -> None:
        """All 5 tabs visible to authenticated users."""
        for tab in self.AUTHED_TABS:
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()
