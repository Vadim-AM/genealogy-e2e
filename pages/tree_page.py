"""POM for / (index.html) — public family tree.

Selectors verified against js/views/orbit.js + js/search.js (28.04 review):
- Orbit cards: `[data-testid="orbit-card"]`
- Search results: `#personSearchResults > .nav-search-result`
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from playwright.sync_api import Locator, Page, expect

from api import routes
from assertions.base import should
from framework.step import step
from pages.profile_panel import ProfilePanel
from src.texts import ErrMsg, Placeholders, t

from .base import BasePage

if TYPE_CHECKING:
    from playwright.sync_api import Expect


class TreePage(BasePage):
    URL = "/"

    # Guests only see tree + about; map/sources/timeline are auth-gated.
    GUEST_TABS = ["tree", "about"]
    AUTHED_TABS = ["tree", "map", "sources", "timeline", "about"]

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Locator properties ──────────────────────────────────────────

    @property
    def h1(self) -> Locator:
        """Заголовок h1."""
        return self.page.get_by_role("heading", level=1)

    @property
    def tab_tree(self) -> Locator:
        """no semantic: switch_tab() uses data-tab"""
        return self.page.locator('[data-tab="tree"]')

    @property
    def tab_map(self) -> Locator:
        """no semantic: switch_tab() uses data-tab"""
        return self.page.locator('[data-tab="map"]')

    @property
    def tab_sources(self) -> Locator:
        """no semantic: switch_tab() uses data-tab"""
        return self.page.locator('[data-tab="sources"]')

    @property
    def tab_timeline(self) -> Locator:
        """no semantic: switch_tab() uses data-tab"""
        return self.page.locator('[data-tab="timeline"]')

    @property
    def tab_about(self) -> Locator:
        """no semantic: switch_tab() uses data-tab"""
        return self.page.locator('[data-tab="about"]')

    @property
    def search_input(self) -> Locator:
        """Поле поиска по дереву."""
        return self.page.get_by_placeholder(t(Placeholders.SEARCH_TREE))

    @property
    def search_results_container(self) -> Locator:
        """no semantic: container div"""
        return self.page.locator("#personSearchResults")

    @property
    def search_results(self) -> Locator:
        """no semantic: data-testid items"""
        return self.search_results_container.locator('[data-testid="search-result-item"]')

    @property
    def tree_container(self) -> Locator:
        """no semantic: canvas container"""
        return self.page.locator("#treeContainer")

    @property
    def orbit_cards(self) -> Locator:
        """no semantic: custom canvas cards"""
        return self.tree_container.locator('[data-testid="orbit-card"]')

    @property
    def minimap(self) -> Locator:
        """no semantic: custom widget"""
        return self.page.locator("#minimap")

    @property
    def branch_legend(self) -> Locator:
        """no semantic: custom widget"""
        return self.page.locator("#branchLegend")

    @property
    def auth_indicator(self) -> Locator:
        """no semantic: custom widget"""
        return self.page.locator("#authIndicator")

    @property
    def tour_replay_btn(self) -> Locator:
        """no semantic: dynamically shown"""
        return self.page.locator("#tourReplayBtn")

    @property
    def orbit_center(self) -> Locator:
        """no semantic: canvas card, no ARIA"""
        return self.tree_container.locator('[data-testid="orbit-center-card"]')

    @property
    def auth_user_name(self) -> Locator:
        """no semantic: auth UI elements, no ARIA roles"""
        return self.auth_indicator.locator('[data-testid="auth-user-name"]')

    @property
    def logout_btn(self) -> Locator:
        """no semantic: auth UI elements, no ARIA roles"""
        return self.auth_indicator.locator('a[data-action="logout"]')

    @property
    def login_link(self) -> Locator:
        """no semantic: auth login link"""
        return self.page.locator('#authIndicator a[href="/login"]')

    # ── Tab content locators ────────────────────────────────────────

    @property
    def sources_footer_ornament(self) -> Locator:
        """no semantic: tab without role="tab"; decorative element"""
        return self.page.locator('#tab-sources [data-testid="footer-ornament"]')

    @property
    def timeline_footer_ornament(self) -> Locator:
        """no semantic: decorative element"""
        return self.page.locator('#tab-timeline [data-testid="footer-ornament"]')

    @property
    def river_filters(self) -> Locator:
        """no semantic: custom filter, no button role"""
        return self.page.locator('#riverFilters button[data-testid^="river-filter"]')

    @property
    def sources_search(self) -> Locator:
        """no semantic: input without label"""
        return self.page.locator("#evidenceSearch")

    @property
    def sources_filter_all(self) -> Locator:
        """no semantic: custom filter button"""
        return self.page.locator('.filter-btn[data-filter="all"]')

    @property
    def about_placeholder(self) -> Locator:
        """no semantic: content container"""
        return self.page.locator('[data-config-empty="about_text"]')

    @property
    def contact_text(self) -> Locator:
        """no semantic: content container"""
        return self.page.locator('[data-testid="contact-text"]')

    @property
    def contact_email(self) -> Locator:
        """no semantic: content container"""
        return self.page.locator('[data-testid="contact-email"]')

    @property
    def contact_box_placeholder(self) -> Locator:
        """no semantic: placeholder container"""
        return self.page.locator("#contactBoxPlaceholder")

    @property
    def about_beta_card(self) -> Locator:
        """no semantic: content card, no ARIA"""
        return self.page.locator("#aboutBetaCard")

    @property
    def about_cta_link(self) -> Locator:
        """CTA link to /wait inside the beta card."""
        return self.about_beta_card.locator('a[href="/wait"]')

    # ── Сценарные методы (auth state) ─────────────────────────────────

    def expect_authed_state(self, display_name: str | None = None) -> None:
        """Ожидает authed-shell и проверяет имя пользователя + logout-ссылку."""
        with step("ожидание authed-состояния"):
            expect(self.orbit_cards.first).to_be_visible()
            if display_name:
                expect(self.auth_user_name).to_have_text(display_name)
            expect(self.logout_btn).to_be_visible()

    def wait_for_auth_resolved(self, *, expected: bool = True, timeout_ms: int = 5_000) -> None:
        """Poll window.AUTH.authenticated until it matches expected or timeout.

        Deep links race the /api/auth/me round-trip; this waits for the JS
        auth state to settle rather than relying on DOM side-effects.
        """
        self.page.wait_for_function(
            "(want) => window.AUTH && window.AUTH.authenticated === want",
            arg=expected,
            timeout=timeout_ms,
        )

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
        with step("клик «Выйти»"):
            with self.page.expect_response(
                lambda r: routes.LOGOUT in r.url and r.request.method == "POST"
            ):
                self.logout_btn.click()

    # ── Навигация к профилю ──────────────────────────────────────────

    def open_center_profile(self) -> ProfilePanel:
        """Клик по центральной orbit-карточке → открывает профиль demo-self."""

        with step("клик по orbit-center → открытие профиля"):
            expect(self.orbit_center).to_be_visible()
            self.orbit_center.click()
            panel = ProfilePanel(self.page)
            panel.expect_visible()
            return panel

    def reload(self) -> Self:
        """Reload the page and wait for DOM content loaded."""
        with step("действие: перезагрузка страницы"):
            self.page.reload()
            self.page.wait_for_load_state("domcontentloaded")
        return self

    def switch_tab(self, tab_name: str) -> Self:
        """Click a tab and wait for the page to settle.

        tab_name: 'tree' | 'map' | 'sources' | 'timeline' | 'about'.
        """
        self.tab_locator(tab_name).click()
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
        should.greater_or_equal(count, min_cards, ErrMsg.orbit_card_not_visible)

    def tab_content_pane(self, tab_name: str) -> Locator:
        """Return the tab content pane locator (`#tab-<name>.active`)."""
        return self.page.locator(f"#tab-{tab_name}.active")

    def expect_tab_content_active(self, tab_name: str) -> None:
        """Assert the tab content pane is active (`#tab-<name>.active`)."""
        expect(
            self.tab_content_pane(tab_name),
            ErrMsg.tab_not_visible,
        ).to_be_visible()

    def footer_link(self, href: str) -> Locator:
        """Return the first footer link matching the given href."""
        return self.page.locator(f"a[href='{href}']").first

    def footer_link_target(self, href: str) -> str | None:
        """Return the target attribute of a footer link."""
        return self.footer_link(href).get_attribute("target")

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

    def click_river_filter(self, branch: str) -> Self:
        """Click a river-filter button by branch name."""
        with step(f"действие: клик по фильтру {branch!r}"):
            self.river_filter_btn(branch).click()
        return self

    def river_filter_branches(self) -> list[str | None]:
        """Return the list of data-branch values for all river-filter buttons."""
        return [
            self.river_filters.nth(i).get_attribute("data-branch")
            for i in range(self.river_filters.count())
        ]

    def sources_search_placeholder(self) -> str | None:
        """Return the placeholder attribute of the sources search input."""
        return self.sources_search.get_attribute("placeholder")

    def click_orbit_card(self, card: Locator) -> None:
        """Click an orbit card (e.g. to recenter the orbit view)."""
        with step("действие: клик по orbit-карточке"):
            card.click()

    def orbit_card_person_id(self, card: Locator) -> str | None:
        """Return the data-person-id attribute of an orbit card."""
        return card.get_attribute("data-person-id")

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

    def search_and_open_profile(self, query: str) -> ProfilePanel:
        """Search for a person, click result, open profile via center card."""

        with step(f"действие: найти и открыть профиль {query!r}"):
            with self.page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
                self.goto()
            self.search_input.fill(query)
            expect(self.search_results.first).to_be_visible()
            self.search_results.first.click()
            expect(self.orbit_center).to_contain_text(query)
            self.orbit_center.click()
            panel = ProfilePanel(self.page)
            panel.expect_visible()
            return panel

    def search_and_orbit(self, query: str) -> Self:
        """Search for a person, click result, stay on orbit view."""
        with step(f"действие: найти и сфокусировать {query!r}"):
            with self.page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
                self.goto()
            self.search_input.fill(query)
            expect(self.search_results.first).to_be_visible()
            self.search_results.first.click()
            expect(self.orbit_center).to_be_visible()
            return self



    @property
    def header_search(self) -> Locator:
        """Return the #headerSearch locator."""
        return self.page.locator("#headerSearch")  # no semantic: form input without label

    def soft_check_guest_tabs(self, soft: Expect) -> None:
        """Tabs visible to anonymous visitors (tree + about)."""
        for tab in self.GUEST_TABS:
            soft(self.tab_locator(tab)).to_be_visible()

    def soft_check_authed_tabs(self, soft: Expect) -> None:
        """All 5 tabs visible to authenticated users."""
        for tab in self.AUTHED_TABS:
            soft(self.tab_locator(tab)).to_be_visible()
