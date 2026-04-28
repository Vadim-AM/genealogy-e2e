"""Smoke tests — verify the e2e infrastructure boots and basic pages render.

These are the canary for the whole suite: if these fail, conftest fixtures
(uvicorn subprocess, AI mock, reset endpoint, Page Objects) need fixing
before bothering with the rest.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.pages.signup_page import SignupPage
from tests.pages.tree_page import TreePage
from tests.pages.wait_page import WaitPage


@pytest.mark.smoke
def test_landing_loads(page: Page, base_url: str):
    """F-LND-1/2: GET / → 200, HTML, title contains brand."""
    tree = TreePage(page).goto()
    expect(page).not_to_have_url("about:blank")
    expect(tree.h1).to_be_visible()


@pytest.mark.smoke
def test_signup_form_visible(page: Page):
    """F-SU-1: /signup renders form with required inputs."""
    signup = SignupPage(page).goto()
    signup.expect_visible_form()


@pytest.mark.smoke
def test_wait_form_visible(page: Page):
    """C-LND-1 + waitlist scope: /wait renders form."""
    wait = WaitPage(page).goto()
    wait.expect_visible_form()


@pytest.mark.smoke
def test_health_endpoint_via_browser(page: Page):
    """Sanity: even page.goto sees the live FastAPI subprocess."""
    response = page.goto("/api/health")
    assert response is not None
    assert response.status == 200
