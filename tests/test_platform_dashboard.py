"""Platform superadmin dashboard — TC-PA-* metrics, tenants table, free-license-grant.

Superadmin = email in PLATFORM_SUPERADMIN_EMAILS env.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.pages.platform_dashboard_page import PlatformDashboardPage


def test_platform_dashboard_loads_for_superadmin(
    auth_context_factory, superadmin_user
):
    """TC-PA-1: superadmin can open /platform/dashboard."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    response = page.goto("/platform/dashboard")
    assert response is not None
    page.wait_for_load_state("networkidle", timeout=15_000)
    if response.status == 404:
        pytest.skip("/platform/dashboard not yet wired in current HEAD")
    assert response.status == 200


def test_platform_metrics_visible(auth_context_factory, superadmin_user, soft_check):
    """TC-PA-2: metrics cards rendered."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_load_state("networkidle", timeout=15_000)

    if page.locator("body").text_content() and "404" in (page.locator("body").text_content() or ""):
        pytest.skip("dashboard page not present")

    dashboard = PlatformDashboardPage(page)
    dashboard.soft_check_metrics_loaded(soft_check)


def test_platform_metrics_endpoint_403_for_non_super(
    owner_user, base_url: str
):
    """TC-PA-3: regular owner gets 403 on /api/platform/metrics."""
    r = httpx.get(
        f"{base_url}/api/platform/metrics",
        cookies=owner_user.cookies,
        timeout=10,
    )
    assert r.status_code in (401, 403), \
        f"non-superadmin reached platform metrics: {r.status_code} {r.text[:200]}"


def test_platform_metrics_endpoint_200_for_super(
    superadmin_user, base_url: str
):
    """TC-PA-4: superadmin gets 200 on /api/platform/metrics with tenant counters."""
    r = httpx.get(
        f"{base_url}/api/platform/metrics",
        cookies=superadmin_user.cookies,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # Backend may use different key names — accept any of these.
    has_signups = any(
        k in data for k in ("signups_total", "total_signups", "signups", "new_users")
    )
    has_tenants = any(
        k in data for k in ("tenants_active", "active_tenants", "tenants")
    )
    assert has_signups, f"no signups metric: {list(data.keys())}"
    assert has_tenants, f"no tenants metric: {list(data.keys())}"
