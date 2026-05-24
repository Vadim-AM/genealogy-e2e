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

from typing import TYPE_CHECKING

import allure

from tests._core.api_paths import API
from tests._core.constants import make_email
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests.helpers.api import person_api, site_api
from tests.pages.signup_page import SignupPage

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from tests._fixtures.page_factory import PageFactory


@allure.title("Регрессия: auth_v2 владелец читает историю обогащения")
def test_bug_auth_001_authv2_owner_reads_enrichment(
    owner_user, grant_ai_consent, tenant_client,
):
    """TC-BUG-AUTH-001: auth_v2 owner can hit GET /api/enrich/{id}/history without 401."""
    with step("подготовка: consent и получение pid"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        assert tree.people, "new tenant must have demo people seeded"
        pid = tree.people[0].id

    with step("проверка: history и acceptances доступны (200/204)"):
        for path in (API.enrich_history(pid), API.enrich_acceptances(pid)):
            r = api.get(path)
            expect_response(r, label=f"GET {path}").status(200, 204)


@allure.title("Регрессия: аналитика page_view не падает с 500")
def test_bug_auth_002_pageview_platform_session_no_500(owner_user, tenant_client):
    """TC-BUG-AUTH-002: /api/analytics/log with PlatformSession cookie returns 204.

    Pinned exact status (was `< 500` smoke per rule #1). Backend
    contract is fire-and-forget — 204 No Content on accepted event.
    """
    with step("действие: отправка page_view аналитики"):
        api = tenant_client(owner_user)
        r = api.post(
            API.ANALYTICS_LOG,
            json={"event": "page_view", "path": "/", "context": {"section": "tree"}},
        )

    with step("проверка: endpoint вернул 200"):
        expect_response(r, label="BUG-AUTH-002 analytics log").status(200)


@allure.title("Регрессия: /signup не запрашивает /api/csrf-token (404)")
def test_bug_csrf_001_console_clean_on_signup(page: Page, anon_pages: PageFactory):
    """TC-BUG-CSRF-001: opening /signup → no 404 on /api/csrf-token in console."""
    with step("действие: открыть /signup и слушать 404 на /api/csrf-token"):
        bad_404: list[str] = []
        page.on(
            "response",
            lambda r: bad_404.append(r.url)
            if r.status == 404 and "/api/csrf-token" in r.url
            else None,
        )
        anon_pages.navigate_to(SignupPage)

    with step("проверка: нет 404 на /api/csrf-token"):
        assert not bad_404, f"BUG-CSRF-001 regression: {bad_404}"


@allure.title("Регрессия: site_config изолирован между тенантами")
def test_bug_mt_001_site_config_is_per_tenant(signup_via_api, tenant_client):
    """BUG-MT-001 regression: PATCH /api/site/config in tenant A must NOT affect tenant B.

    Was xfail (Apr 2026) — passes in current HEAD; marker dropped on 28.04.
    """
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api(email=make_email("config-a"))
        user_b = signup_via_api(email=make_email("config-b"))
        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: изменить site_name в тенанте A"):
        site_api.patch_site_config(api_a, site_name="Tenant A Brand")

    with step("проверка: тенант B не содержит site_name тенанта A"):
        config_b = site_api.get_site_config(api_b)
        assert config_b.site_name != "Tenant A Brand", \
            "BUG-MT-001: tenant A's config leaked into tenant B"


@allure.title("Регрессия: повторный запрос обогащения не даёт 409")
def test_bug_auth_003_sse_reconnect_recovers(
    owner_user, grant_ai_consent, tenant_client,
):
    """TC-BUG-AUTH-003 regression: re-issuing a streaming enrichment for the
    same person must reuse the active job, not 409 Conflict."""
    with step("подготовка: consent и получение pid"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        assert tree.people, "new tenant must have demo people seeded"
        pid = tree.people[0].id

    with step("действие: первый streaming enrichment POST"):
        r1 = api.post(
            API.enrich(pid),
            json={"streaming": True, "force_refresh": False},
            timeout=TIMEOUTS.api_long,
        )
        expect_response(r1, label="first enrich POST").status(200)

    with step("проверка: повторный POST возвращает 200, не 409"):
        r2 = api.post(
            API.enrich(pid),
            json={"streaming": True, "force_refresh": False},
            timeout=TIMEOUTS.api_long,
        )
        expect_response(r2, label="BUG-AUTH-003 reconnect").status(200)
