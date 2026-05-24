"""POM for / (index.html) — public family tree.

Selectors verified against js/views/orbit.js + js/search.js (28.04 review):
- Orbit cards: `[data-testid="orbit-card"]`
- Search results: `#personSearchResults > .nav-search-result`
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from src.texts import Placeholders, t

from .base import BasePage


class TreePage(BasePage):
    URL = "/"

    # Guests only see tree + about; map/sources/timeline are auth-gated.
    GUEST_TABS = ["tree", "about"]
    AUTHED_TABS = ["tree", "map", "sources", "timeline", "about"]

    def __init__(self, page: Page):
        super().__init__(page)
        self.h1 = page.get_by_role("heading", level=1)
        self.tab_tree = page.locator('[data-tab="tree"]')  # no semantic: switch_tab() uses data-tab
        self.tab_map = page.locator('[data-tab="map"]')  # no semantic: switch_tab() uses data-tab
        self.tab_sources = page.locator('[data-tab="sources"]')  # no semantic: switch_tab() uses data-tab
        self.tab_timeline = page.locator('[data-tab="timeline"]')  # no semantic: switch_tab() uses data-tab
        self.tab_about = page.locator('[data-tab="about"]')  # no semantic: switch_tab() uses data-tab
        self.search_input = page.get_by_placeholder(t(Placeholders.SEARCH_TREE))
        self.search_results_container = page.locator("#personSearchResults")  # no semantic: container div
        self.search_results = self.search_results_container.locator(  # no semantic: data-testid items
            '[data-testid="search-result-item"]'
        )
        self.tree_container = page.locator("#treeContainer")  # no semantic: canvas container
        self.orbit_cards = self.tree_container.locator('[data-testid="orbit-card"]')  # no semantic: custom canvas cards
        self.minimap = page.locator("#minimap")  # no semantic: custom widget
        self.branch_legend = page.locator("#branchLegend")  # no semantic: custom widget
        self.auth_indicator = page.locator("#authIndicator")  # no semantic: custom widget
        self.tour_replay_btn = page.locator("#tourReplayBtn")  # no semantic: dynamically shown

    def switch_tab(self, tab_name: str) -> Self:
        """Click a tab and wait for the page to settle.

        tab_name: 'tree' | 'map' | 'sources' | 'timeline' | 'about'.
        """
        self.page.locator(f'[data-tab="{tab_name}"]').click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    # backward-compat alias (used by existing tests)
    switch_to = switch_tab

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

    def search_person(self, query: str) -> Self:
        """Type a search query into the tree search input."""
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
