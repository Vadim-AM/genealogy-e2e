"""Onboarding demo-data journeys — clear or keep the seeded demo relatives.

A fresh tenant seeds demo people (Иван, Мария …). In owner settings the
owner chooses to erase them outright or keep them as an editable
template. Two tenants — each test gets its own owner — so the two
mutually-exclusive choices are exercised independently.
"""

from __future__ import annotations

from playwright.sync_api import Page

from tests.api_paths import API
from tests.messages import Onboarding, t


def test_owner_clears_demo_relatives(owner_page: Page, owner_user, tenant_client):
    """Owner opens settings → 'Стереть демо-родственников' → confirms →
    the demo people are removed from the tree."""
    api = tenant_client(owner_user)
    before = api.get(API.TREE).json()["people"]
    assert len(before) > 1, "a fresh tenant seeds demo relatives"

    owner_page.goto("/owner")
    owner_page.wait_for_load_state("domcontentloaded")
    with owner_page.expect_response("**/api/onboarding/clear-demo"):
        owner_page.locator("#clearDemo").click()
        owner_page.locator(".confirm-dialog").get_by_role(
            "button", name=t(Onboarding.CLEAR_DEMO_CONFIRM), exact=True
        ).click()

    after = api.get(API.TREE).json()["people"]
    assert len(after) < len(before), \
        f"demo relatives must be gone: {len(before)} → {len(after)}"


def test_owner_keeps_demo_as_template(owner_page: Page, owner_user, tenant_client):
    """Owner opens settings → 'Использовать как шаблон' → confirms →
    the tree structure stays (people are kept, not deleted)."""
    api = tenant_client(owner_user)
    before = api.get(API.TREE).json()["people"]
    assert len(before) > 1, "a fresh tenant seeds demo relatives"

    owner_page.goto("/owner")
    owner_page.wait_for_load_state("domcontentloaded")
    with owner_page.expect_response("**/api/onboarding/keep-demo"):
        owner_page.locator("#keepDemo").click()
        owner_page.locator(".confirm-dialog").get_by_role(
            "button", name=t(Onboarding.KEEP_DEMO_CONFIRM), exact=True
        ).click()

    after = api.get(API.TREE).json()["people"]
    assert len(after) == len(before), \
        f"keep-as-template must preserve the structure: {len(before)} → {len(after)}"
