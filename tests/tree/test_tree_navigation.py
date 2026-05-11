"""Tree navigation, F5-routing, tabs, search.

Covers: TC-E2E-002 (F5 keeps profile), F-FV-4 tabs.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.messages import TestData
from tests.pages.tree_page import TreePage


def test_switch_between_tabs(owner_page: Page):
    """F-FV-4: switching tabs updates active class + content."""
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")

    for tab_name in ("map", "sources", "timeline", "about"):
        tree.switch_to(tab_name)
        # No fixed sleep: `expect` auto-waits until the .active class
        # transition is observed in DOM.
        expect(owner_page.locator(f'.tab[data-tab="{tab_name}"].active')).to_be_visible()
        expect(owner_page.locator(f"#tab-{tab_name}.active")).to_be_visible()


def test_search_returns_results_for_seeded_person(owner_page: Page):
    """F-FV-5: typing a seeded person's name surfaces matching results.

    `signup_via_api` defaults `full_name="Тестовый Пользователь"` which is
    persisted as the demo-self person's `name`. Searching "Тест" must
    hydrate `#personSearchResults` with `.nav-search-result` items.
    """
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")
    tree.search_person("Тест")
    expect(tree.search_results.first).to_be_visible()


def test_f5_keeps_profile_open(owner_page: Page):
    """TC-E2E-002: F5 on a profile URL keeps the profile route, не выкидывает в дерево."""
    profile_hash = f"#/p/{TestData.DEMO_PERSON_ID}"
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")

    owner_page.goto("/" + profile_hash)
    owner_page.wait_for_load_state("networkidle")

    owner_page.reload()
    owner_page.wait_for_load_state("networkidle")
    assert profile_hash in owner_page.url, f"hash dropped after F5: {owner_page.url}"


def test_back_to_tree_from_profile(owner_page: Page):
    """F-PR-4: returning to tree from profile via tab click."""
    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("networkidle")
    owner_page.locator('[data-tab="tree"]').click()
    expect(owner_page.locator('.tab[data-tab="tree"].active')).to_be_visible()
