"""Regression suite for closed BUG-* tickets per docs/test-plan.md.

Each test maps 1:1 to a TC-BUG-*. Open bugs are marked `xfail` outside the
test body (no runtime `pytest.xfail`). XPASS surfaces as a signal to flip
the marker into a regular regression.

Removed (28.04 sanitize):
- `test_bug_legal_001_html_render` — duplicate of `test_legal_pages.py`.
- `test_bug_copy_001_wait_no_owner_pii` — duplicate of
  `test_waitlist::test_wait_no_owner_personal_data`.
- `test_bug_log_001_500_writes_to_log` — only asserted /api/health works
  (no actual logging check). Reinstate when a synthetic 500-trigger
  endpoint exists in backend (`/api/_test/raise-500`).
"""

from __future__ import annotations

import httpx

from tests.timeouts import TIMEOUTS
from playwright.sync_api import Page


def test_bug_auth_001_authv2_owner_reads_enrichment(owner_user, base_url: str):
    """TC-BUG-AUTH-001: auth_v2 owner can hit GET /api/enrich/{id}/history without 401."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, f"new tenant must have demo people seeded; got: {r.json()}"
    pid = people[0]["id"]

    for sub in ("/history", "/acceptances"):
        r = httpx.get(
            f"{base_url}/api/enrich/{pid}{sub}",
            cookies=owner_user.cookies,
            headers=headers,
            timeout=TIMEOUTS.api_request,
        )
        assert r.status_code != 401, \
            f"BUG-AUTH-001 regression: GET /api/enrich/{pid}{sub} → 401"
        # 200 = success with data, 204 = empty list. 4xx of any other shape
        # means coverage regression — fail loudly.
        assert r.status_code in (200, 204), \
            f"unexpected status for {pid}{sub}: {r.status_code} {r.text[:200]}"


def test_bug_auth_002_pageview_platform_session_no_500(owner_user, base_url: str):
    """TC-BUG-AUTH-002: /api/analytics/log with PlatformSession cookie does not 500."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/analytics/log",
        json={"event": "page_view", "path": "/", "context": {"section": "tree"}},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code < 500, \
        f"BUG-AUTH-002 regression: 5xx with body {r.text[:300]}"


def test_bug_csrf_001_console_clean_on_signup(page: Page):
    """TC-BUG-CSRF-001: opening /signup → no 404 on /api/csrf-token in console."""
    bad_404: list[str] = []
    page.on(
        "response",
        lambda r: bad_404.append(r.url)
        if r.status == 404 and "/api/csrf-token" in r.url
        else None,
    )
    page.goto("/signup")
    page.wait_for_load_state("networkidle")
    assert not bad_404, f"BUG-CSRF-001 regression: {bad_404}"


def test_bug_mt_001_site_config_is_per_tenant(signup_via_api, base_url: str):
    """BUG-MT-001 regression: PATCH /api/site/config in tenant A must NOT affect tenant B.

    Was xfail (Apr 2026) — passes in current HEAD; marker dropped on 28.04.
    """
    user_a = signup_via_api(email="config-a@e2e.example.com")
    user_b = signup_via_api(email="config-b@e2e.example.com")

    r = httpx.patch(
        f"{base_url}/api/site/config",
        json={"site_name": "Tenant A Brand"},
        cookies=user_a.cookies,
        headers={"X-Tenant-Slug": user_a.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()

    r = httpx.get(
        f"{base_url}/api/site/config",
        cookies=user_b.cookies,
        headers={"X-Tenant-Slug": user_b.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["site_name"] != "Tenant A Brand", \
        "BUG-MT-001: tenant A's config leaked into tenant B"


def test_bug_auth_003_sse_reconnect_recovers(owner_user, base_url: str):
    """TC-BUG-AUTH-003 regression: re-issuing a streaming enrichment for the
    same person must reuse the active job, not 409 Conflict."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, "new tenant must have demo people seeded"
    pid = people[0]["id"]

    r1 = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": True, "force_refresh": False},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    assert r1.status_code == 200, \
        f"first enrich POST failed: {r1.status_code} {r1.text[:200]}"

    r2 = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": True, "force_refresh": False},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    assert r2.status_code != 409, \
        f"BUG-AUTH-003 regression on reconnect: {r2.text[:200]}"
    assert r2.status_code == 200, \
        f"reconnect failed: {r2.status_code} {r2.text[:200]}"
