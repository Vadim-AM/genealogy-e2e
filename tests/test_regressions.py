"""Regression suite for closed BUG-* tickets per docs/test-plan.md.

Each test maps 1:1 to a closed TC-BUG-*. Open bugs are NOT tested here —
they live in project memory + an upstream issue until fixed, then get a
green regression test (the suite has no xfail markers — see CLAUDE.md
Rule 12).

Removed (28.04 sanitize):
- `test_bug_legal_001_html_render` — duplicate of `test_legal_pages.py`.
- `test_bug_copy_001_wait_no_owner_pii` — duplicate of
  `test_waitlist::test_wait_no_owner_personal_data`.
- `test_bug_log_001_500_writes_to_log` — only asserted /api/health works
  (no actual logging check). Reinstate when a synthetic 500-trigger
  endpoint exists in backend (`/api/_test/raise-500`).
"""

from __future__ import annotations

from playwright.sync_api import Page

import allure

from tests.api_paths import API
from tests.constants import make_email
from tests.response import expect_response
from tests.timeouts import TIMEOUTS


@allure.title("Регрессия: auth_v2 владелец читает историю обогащения")
def test_bug_auth_001_authv2_owner_reads_enrichment(
    owner_user, grant_ai_consent, tenant_client,
):
    """TC-BUG-AUTH-001: auth_v2 owner can hit GET /api/enrich/{id}/history without 401."""
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)
    r = api.get(API.TREE)
    expect_response(r, label="tree").status_ok().json_has("people")
    people = r.json()["people"]
    assert people, f"new tenant must have demo people seeded; got: {r.json()}"
    pid = people[0]["id"]

    for path in (API.enrich_history(pid), API.enrich_acceptances(pid)):
        r = api.get(path)
        expect_response(r, label=f"GET {path}").status(200, 204)


@allure.title("Регрессия: аналитика page_view не падает с 500")
def test_bug_auth_002_pageview_platform_session_no_500(owner_user, tenant_client):
    """TC-BUG-AUTH-002: /api/analytics/log with PlatformSession cookie returns 204.

    Pinned exact status (was `< 500` smoke per rule #1). Backend
    contract is fire-and-forget — 204 No Content on accepted event.
    """
    api = tenant_client(owner_user)
    r = api.post(
        API.ANALYTICS_LOG,
        json={"event": "page_view", "path": "/", "context": {"section": "tree"}},
    )
    expect_response(r, label="BUG-AUTH-002 analytics log").status(200)


@allure.title("Регрессия: /signup не запрашивает /api/csrf-token (404)")
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
    page.wait_for_load_state("domcontentloaded")
    assert not bad_404, f"BUG-CSRF-001 regression: {bad_404}"


@allure.title("Регрессия: site_config изолирован между тенантами")
def test_bug_mt_001_site_config_is_per_tenant(signup_via_api, tenant_client):
    """BUG-MT-001 regression: PATCH /api/site/config in tenant A must NOT affect tenant B.

    Was xfail (Apr 2026) — passes in current HEAD; marker dropped on 28.04.
    """
    user_a = signup_via_api(email=make_email("config-a"))
    user_b = signup_via_api(email=make_email("config-b"))

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    expect_response(
        api_a.patch(API.SITE_CONFIG, json={"site_name": "Tenant A Brand"}),
        label="patch site config A",
    ).status_ok()

    r = api_b.get(API.SITE_CONFIG)
    expect_response(r, label="get site config B").status_ok()
    assert r.json()["site_name"] != "Tenant A Brand", \
        "BUG-MT-001: tenant A's config leaked into tenant B"


@allure.title("Регрессия: повторный запрос обогащения не даёт 409")
def test_bug_auth_003_sse_reconnect_recovers(
    owner_user, grant_ai_consent, tenant_client,
):
    """TC-BUG-AUTH-003 regression: re-issuing a streaming enrichment for the
    same person must reuse the active job, not 409 Conflict."""
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)
    r = api.get(API.TREE)
    expect_response(r, label="tree").status_ok().json_has("people")
    people = r.json()["people"]
    assert people, "new tenant must have demo people seeded"
    pid = people[0]["id"]

    r1 = api.post(
        API.enrich(pid),
        json={"streaming": True, "force_refresh": False},
        timeout=TIMEOUTS.api_long,
    )
    expect_response(r1, label="first enrich POST").status(200)

    r2 = api.post(
        API.enrich(pid),
        json={"streaming": True, "force_refresh": False},
        timeout=TIMEOUTS.api_long,
    )
    expect_response(r2, label="BUG-AUTH-003 reconnect").status(200)
