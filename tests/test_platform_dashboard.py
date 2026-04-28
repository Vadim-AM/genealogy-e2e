"""Platform superadmin dashboard — TC-PA-* metrics, tenants table, free-license-grant.

Superadmin = email in PLATFORM_SUPERADMIN_EMAILS env. Suite ships
`super@e2e.example.com` as the canonical superadmin.
"""

from __future__ import annotations

import httpx

from tests.timeouts import TIMEOUTS

from tests.pages.platform_dashboard_page import PlatformDashboardPage


def test_platform_dashboard_loads_for_superadmin(
    auth_context_factory, superadmin_user
):
    """TC-PA-1: superadmin can open /platform/dashboard.

    404 = unimplemented page (regression). superadmin UI is a Stage 1
    deliverable per docs/test-plan.md.
    """
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    response = page.goto("/platform/dashboard")
    assert response is not None
    assert response.status == 200, \
        f"/platform/dashboard returned {response.status} (regression)"


def test_platform_metrics_visible(auth_context_factory, superadmin_user, soft_check):
    """TC-PA-2: metrics cards rendered."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_load_state("networkidle")

    dashboard = PlatformDashboardPage(page)
    dashboard.soft_check_metrics_loaded(soft_check)


def test_platform_metrics_endpoint_403_for_non_super(owner_user, base_url: str):
    """TC-PA-3: regular owner gets 401 or 403 on /api/platform/metrics."""
    r = httpx.get(
        f"{base_url}/api/platform/metrics",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403), \
        f"non-superadmin reached platform metrics: {r.status_code} {r.text[:200]}"


def test_platform_metrics_endpoint_200_for_super(superadmin_user, base_url: str):
    """TC-PA-4: superadmin gets 200 on /api/platform/metrics with the canonical
    field names.

    Field names verified against `platform_admin.py:136-137`: `tenants_active`,
    `signups_total`. Strict-equality on schema (the keys must exist) — if
    backend renames, the test fails loud.
    """
    r = httpx.get(
        f"{base_url}/api/platform/metrics",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("tenants_active", "signups_total"):
        assert key in data, f"metric {key!r} missing from response: {list(data)}"
        assert isinstance(data[key], int), f"{key} must be int, got {type(data[key])}"
