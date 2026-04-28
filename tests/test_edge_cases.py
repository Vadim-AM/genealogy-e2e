"""Edge cases per docs/test-plan.md TC-EDGE-001..005.

`test_minimap_hidden_on_mobile_viewport` removed during 28.04 sanitize:
the original used a runtime `pytest.xfail` that masked any regression.
Reinstate as `@pytest.mark.xfail(strict=False)` only after BUG status
is confirmed open.
"""

from __future__ import annotations

import httpx

from tests.timeouts import TIMEOUTS
from playwright.sync_api import Page, expect


def test_f5_on_nonexistent_profile_id_does_not_crash(owner_page: Page):
    """TC-EDGE-004: F5 on /#/p/<unknown> shows tree, no JS crash."""
    owner_page.goto("/#/p/nonexistent_xyz_123")
    owner_page.wait_for_load_state("networkidle")
    expect(owner_page.locator('[data-tab="tree"]')).to_be_visible()


def test_old_person_with_only_name_field_renders(owner_user, base_url: str):
    """TC-EDGE-001: a person record with only `name` (no surname/given) — accessible.

    If POST /api/people stops accepting the legacy single-name payload, that's
    a backwards-compatibility regression and the test must fail loud.
    """
    headers = {"X-Tenant-Slug": owner_user.slug}

    payload = {
        "id": "edge-old-name",
        "name": "Иванов Иван Петрович",
        "branch": "subject",
        "gender": "m",
    }
    r = httpx.post(
        f"{base_url}/api/people",
        json=payload,
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (200, 201), \
        f"POST /api/people legacy payload rejected: {r.status_code} {r.text[:200]}"

    r = httpx.get(
        f"{base_url}/api/people/edge-old-name",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    person = r.json()
    assert "Иван" in (person.get("name") or ""), \
        f"name not preserved: {person.get('name')!r}"


def test_health_endpoint_does_not_require_auth(base_url: str):
    """Smoke: /api/health is public, used by Caddy / monitoring."""
    r = httpx.get(f"{base_url}/api/health", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    assert r.json() == {"status": "ok"}, \
        f"unexpected /api/health body: {r.json()!r}"
