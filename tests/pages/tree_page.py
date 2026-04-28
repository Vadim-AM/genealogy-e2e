"""POM for / (index.html) — public family tree.

Selectors verified against js/views/orbit.js + js/search.js (28.04 review):
- Orbit cards: `.orbit-card`
- Search results: `#personSearchResults > .nav-search-result`
"""

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
        self.search_results_container = page.locator("#personSearchResults")
        self.search_results = self.search_results_container.locator(
            ".nav-search-result[data-action='search-navigate']"
        )
        self.tree_container = page.locator("#treeContainer")
        self.orbit_cards = self.tree_container.locator(".orbit-card")
        self.minimap = page.locator("#minimap")
        self.auth_indicator = page.locator("#authIndicator")
        self.tour_replay_btn = page.locator("#tourReplayBtn")

    def switch_to(self, tab_name: str) -> "TreePage":
        """tab_name: 'tree' | 'map' | 'sources' | 'timeline' | 'about'."""
        self.page.locator(f'[data-tab="{tab_name}"]').click()
        return self

    def expect_tree_rendered(self, *, min_cards: int = 1) -> None:
        """Tree is rendered when at least `min_cards` orbit cards are present.

        Note on counts: orbit-view shows only the centered subject plus their
        immediate ring (parents, spouses, children) — not the entire data set.
        For demo-self with 2 demo parents that's 2 ring cards; pass `min_cards=2`
        when relying on the demo seed, or default `1` for a pure rendering
        contract.
        """
        expect(self.tree_container).to_be_visible()
        # Auto-wait until the orbit renderer attaches at least one card.
        expect(self.orbit_cards.first).to_be_visible()
        count = self.orbit_cards.count()
        assert count >= min_cards, \
            f"orbit rendered {count} cards, expected at least {min_cards}"

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
