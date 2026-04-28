"""First visit after login (этап 5-6 funnel).

Covers: F-FV-1..6, F-OB-1..6 (onboarding tour) при первом заходе owner'а в свой tenant.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.pages.tree_page import TreePage


def test_first_visit_renders_tree_with_demo_seed(owner_page: Page):
    """F-FV-1, F-FV-2: owner visits / and sees rendered tree (5 demo cards)."""
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle", timeout=15_000)
    tree.expect_tree_rendered()


def test_first_visit_shows_authed_tabs(owner_page: Page, soft_check):
    """F-FV-4: all 5 navigation tabs visible to authenticated user."""
    tree = TreePage(owner_page).goto()
    owner_page.wait_for_load_state("networkidle", timeout=15_000)
    tree.soft_check_authed_tabs(soft_check)


def test_first_visit_search_input_visible(owner_page: Page):
    """F-FV-5: search input is in the header for authed users."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle", timeout=15_000)
    # `headerSearch` div has `.visible` class added by updateGuestUI when authed.
    search = owner_page.locator("#headerSearch")
    expect(search).to_be_visible(timeout=10_000)


def test_first_visit_tour_replay_button_visible(owner_page: Page):
    """F-FV-6: '?' tour replay button is visible."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle", timeout=15_000)
    tour_btn = owner_page.locator("#tourReplayBtn")
    expect(tour_btn).to_be_visible(timeout=10_000)


def test_me_endpoint_returns_tenant_after_login(owner_user, base_url: str):
    """F-FV-1 backend check: /api/account/me returns user + tenant."""
    r = httpx.get(f"{base_url}/api/account/me", cookies=owner_user.cookies)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("tenant", {}).get("slug") == owner_user.slug
