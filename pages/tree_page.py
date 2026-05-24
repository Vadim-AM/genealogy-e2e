"""POM for / (index.html) — public family tree.

Selectors verified against js/views/orbit.js + js/search.js (28.04 review):
- Orbit cards: `[data-testid="orbit-card"]`
- Search results: `#personSearchResults > .nav-search-result`
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from src.texts import Placeholders, t

from .base import BasePage

if TYPE_CHECKING:
    from playwright.sync_api import Expect

    from pages.profile_panel import ProfilePanel


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
        # no semantic: canvas card, no ARIA
        self.orbit_center = self.tree_container.locator('[data-testid="orbit-center-card"]')
        # no semantic: auth UI elements, no ARIA roles
        self.auth_user_name = self.auth_indicator.locator('[data-testid="auth-user-name"]')
        self.logout_btn = self.auth_indicator.locator('a[data-action="logout"]')
        self.login_link = page.locator('#authIndicator a[href="/login"]')

        # ── Tab content locators ────────────────────────────────────────
        # no semantic: tab without role="tab"; decorative element
        self.sources_footer_ornament = page.locator('#tab-sources [data-testid="footer-ornament"]')
        # no semantic: decorative element
        self.timeline_footer_ornament = page.locator('#tab-timeline [data-testid="footer-ornament"]')
        # no semantic: custom filter, no button role
        self.river_filters = page.locator('#riverFilters button[data-testid^="river-filter"]')
        # no semantic: input without label
        self.sources_search = page.locator("#evidenceSearch")
        # no semantic: custom filter button
        self.sources_filter_all = page.locator('.filter-btn[data-filter="all"]')
        # no semantic: content container
        self.about_placeholder = page.locator('[data-config-empty="about_text"]')
        # no semantic: content container
        self.contact_text = page.locator('[data-testid="contact-text"]')
        # no semantic: content container
        self.contact_email = page.locator('[data-testid="contact-email"]')
        # no semantic: placeholder container
        self.contact_box_placeholder = page.locator("#contactBoxPlaceholder")
        # no semantic: content card, no ARIA
        self.about_beta_card = page.locator("#aboutBetaCard")

    # ── Сценарные методы (auth state) ─────────────────────────────────

    def expect_authed_state(self, display_name: str | None = None) -> None:
        """Ожидает authed-shell и проверяет имя пользователя + logout-ссылку."""
        with step("ожидание authed-состояния"):
            expect(self.orbit_cards.first).to_be_visible()
            if display_name:
                expect(self.auth_user_name).to_have_text(display_name)
            expect(self.logout_btn).to_be_visible()

    def expect_guest_state(self) -> None:
        """Проверяет гостевой режим: login видна, authed-вкладки скрыты."""
        with step("проверка гостевого режима"):
            expect(self.login_link).to_be_visible()
            expect(self.auth_user_name).to_have_count(0)
            expect(self.tab_map).to_be_hidden()
            expect(self.tab_sources).to_be_hidden()
            expect(self.tab_timeline).to_be_hidden()

    def logout(self) -> None:
        """Клик по «Выйти» с ожиданием POST /logout."""
        from api import routes
        with step("клик «Выйти»"):
            with self.page.expect_response(
                lambda r: routes.LOGOUT in r.url and r.request.method == "POST"
            ):
                self.logout_btn.click()

    # ── Навигация к профилю ──────────────────────────────────────────

    def open_center_profile(self) -> ProfilePanel:
        """Клик по центральной orbit-карточке → открывает профиль demo-self."""
        from pages.profile_panel import ProfilePanel

        with step("клик по orbit-center → открытие профиля"):
            expect(self.orbit_center).to_be_visible()
            self.orbit_center.click()
            panel = ProfilePanel(self.page)
            panel.expect_visible()
            return panel

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
        assert count >= min_cards, (
            f"orbit rendered {count} cards, expected at least {min_cards}"
        )

    def expect_tab_content_active(self, tab_name: str) -> None:
        """Assert the tab content pane is active (`#tab-<name>.active`)."""
        from src.texts import ErrMsg
        expect(
            self.page.locator(f"#tab-{tab_name}.active"),
            ErrMsg.tab_not_visible,
        ).to_be_visible()

    def footer_link(self, href: str) -> Locator:
        """Return the first footer link matching the given href."""
        return self.page.locator(f"a[href='{href}']").first

    def tab_locator(self, tab_name: str) -> Locator:
        """Return a tab locator by data-tab name."""
        return self.page.locator(f'[data-tab="{tab_name}"]')

    def search_person(self, query: str) -> Self:
        """Type a search query into the tree search input."""
        self.search_input.fill(query)
        return self

    def river_filter_btn(self, branch: str) -> Locator:
        """Return a river-filter button by branch name (e.g. 'all', 'maternal')."""
        # no semantic: custom filter, no button role
        return self.page.locator(f'[data-testid="river-filter-{branch}"]')

    def river_filter_branches(self) -> list[str | None]:
        """Return the list of data-branch values for all river-filter buttons."""
        return [
            self.river_filters.nth(i).get_attribute("data-branch")
            for i in range(self.river_filters.count())
        ]

    def orbit_card_by_name(self, name: str) -> Locator:
        """Return an orbit card filtered by visible name text."""
        # no semantic: data-testid element, no ARIA
        return self.orbit_cards.filter(has_text=name).first

    def orbit_card_relation(self, card: Locator) -> Locator:
        """Return the relation-label locator inside an orbit card."""
        # no semantic: data-testid element, no ARIA
        return card.locator('[data-testid="orbit-card-relation"]')

    def non_center_orbit_card(self) -> Locator:
        """Return the first non-center orbit card in the tree container."""
        # no semantic: canvas card, no ARIA
        return self.tree_container.locator(
            '[data-testid="orbit-card"][data-person-id]'
            ':not([data-testid="orbit-center-card"])'
        ).first

    def orbit_center_for_person(self, person_id: str) -> Locator:
        """Return the orbit-center card locator for a specific person."""
        # no semantic: canvas card, no ARIA
        return self.page.locator(
            f'.orbit-zone-center [data-testid="orbit-center-card"]'
            f'[data-person-id=\'{person_id}\']'
        )

    def minimap_computed_display(self) -> str:
        """Return the computed CSS display value of the minimap element."""
        return self.minimap.evaluate("(el) => getComputedStyle(el).display")

    def goto_hash(self, fragment: str) -> Self:
        """Navigate to a hash route (e.g. /#/p/some-id) and wait for load."""
        self.page.goto(f"/{fragment}")
        self.page.wait_for_load_state("domcontentloaded")
        return self



    @property
    def header_search(self) -> Locator:
        """Return the #headerSearch locator."""
        return self.page.locator("#headerSearch")  # no semantic: form input without label

    def soft_check_guest_tabs(self, soft: Expect) -> None:
        """Tabs visible to anonymous visitors (tree + about)."""
        for tab in self.GUEST_TABS:
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()

    def soft_check_authed_tabs(self, soft: Expect) -> None:
        """All 5 tabs visible to authenticated users."""
        for tab in self.AUTHED_TABS:
            soft(self.page.locator(f'[data-tab="{tab}"]')).to_be_visible()
