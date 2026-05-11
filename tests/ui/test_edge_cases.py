"""Edge cases per docs/test-plan.md TC-EDGE-001..005.

`test_minimap_hidden_on_mobile_viewport` removed during 28.04 sanitize:
the original used a runtime `pytest.xfail` that masked any regression.
Reinstate as `@pytest.mark.xfail(strict=False)` only after BUG status
is confirmed open.
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


def test_f5_on_nonexistent_profile_id_does_not_crash(owner_page: Page):
    """TC-EDGE-004: F5 on /#/p/<unknown> shows tree, no JS crash."""
    owner_page.goto("/#/p/nonexistent_xyz_123")
    owner_page.wait_for_load_state("networkidle")
    expect(owner_page.locator('[data-tab="tree"]')).to_be_visible()


def test_old_person_with_only_name_field_renders(owner_user, tenant_client):
    """TC-EDGE-001: a person record with only `name` (no surname/given) — accessible.

    If POST /api/people stops accepting the legacy single-name payload, that's
    a backwards-compatibility regression and the test must fail loud.
    """
    api = tenant_client(owner_user)

    payload = {
        "id": "edge-old-name",
        "name": "Иванов Иван Петрович",
        "branch": "subject",
        "gender": "m",
    }
    r = api.post(API.PEOPLE, json=payload)
    assert r.status_code in (200, 201), \
        f"POST {API.PEOPLE} legacy payload rejected: {r.status_code} {r.text[:200]}"

    r = api.get(API.person("edge-old-name"))
    r.raise_for_status()
    name = r.json().get("name") or ""
    assert "Иван" in name, f"name not preserved: {name!r}"


def test_health_endpoint_does_not_require_auth(base_url: str):
    """Smoke: /api/health is public, used by Caddy / monitoring."""
    r = httpx.get(f"{base_url}{API.HEALTH}", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    assert r.json() == {"status": "ok"}, \
        f"unexpected /api/health body: {r.json()!r}"
