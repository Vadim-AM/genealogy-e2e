"""First visit after login (этап 5-6 funnel).

Covers: F-FV-1..6 при первом заходе owner'а в свой tenant.
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page, expect

from tests.pages.tree_page import TreePage


# Demo seed has demo-self + 2 parents around the centred subject =
# 2 orbit cards rendered in the ring view (the centred subject card
# is rendered in a different DOM slot — `#tab-tree .section-title`).
DEMO_SEED_RING_CARDS = 2


def test_first_visit_renders_tree_with_demo_seed(owner_page: Page):
    """F-FV-1, F-FV-2: owner visits / and orbit-view renders the demo ring.

    Concrete count assertion via `.orbit-card` selector — beats the prior
    "loading indicator hid" smoke. Backend seeds 5 persons; orbit shows
    the centered subject plus immediate ring (parents) = 2 cards visible.
    """
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")
    tree.expect_tree_rendered(min_cards=DEMO_SEED_RING_CARDS)


def test_first_visit_shows_authed_tabs(owner_page: Page):
    """F-FV-4: all 5 navigation tabs visible to authenticated user."""
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle")
    expect(tree.tab_tree).to_be_visible()
    expect(tree.tab_map).to_be_visible()
    expect(tree.tab_sources).to_be_visible()
    expect(tree.tab_timeline).to_be_visible()
    expect(tree.tab_about).to_be_visible()


def test_first_visit_search_input_visible(owner_page: Page):
    """F-FV-5: search input is in the header for authed users."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")
    expect(owner_page.locator("#headerSearch")).to_be_visible()


def test_first_visit_tour_replay_button_visible(owner_page: Page):
    """F-FV-6: '?' tour replay button is visible."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")
    expect(owner_page.locator("#tourReplayBtn")).to_be_visible()


def test_me_endpoint_returns_tenant_after_login(owner_user, base_url: str):
    """F-FV-1 backend check: /api/account/me returns user + tenant slug."""
    r = httpx.get(f"{base_url}/api/account/me", cookies=owner_user.cookies)
    r.raise_for_status()
    assert r.json()["tenant"]["slug"] == owner_user.slug
