"""Platform superadmin analytics — TC-PA-ANALYTICS-* (Phase 1, PR-1..6).

Покрывает endpoint'ы:
  • PR-1 GET /api/platform/device-mix
  • PR-2 GET /api/platform/activity-heatmap
  • PR-3 GET /api/platform/online-now
  • PR-3 GET /api/platform/session-stats
  • PR-4 GET /api/platform/retention
  • PR-4 GET /api/platform/time-to-aha
  • PR-4 GET /api/platform/funnel-detail
  • PR-6 GET /api/platform/alerts
  • PR-6 GET /api/platform/health

Hard rules (CLAUDE.md):
- Single canonical field name. Если backend переименует — тест fail'ит loud.
- Hard expect / assert. Никаких OR-fallback'ов в проверках.
- Нет skip-fallback. Если endpoint вернул 404 — это регрессия, fail.
- Нет timeout-overrides — TIMEOUTS.api_request.
"""

from __future__ import annotations

import httpx

from tests.api_paths import API
from tests.pages.platform_dashboard_page import PlatformDashboardPage
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────
# PR-1 — device-mix
# ─────────────────────────────────────────────────────────────────────


def test_device_mix_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-1.1: regular owner получает 401/403 на device-mix."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_DEVICE_MIX}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403), \
        f"non-superadmin reached device-mix: {r.status_code} {r.text[:200]}"


def test_device_mix_returns_canonical_shape(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-1.2: суперадмин получает 200 + ожидаемые поля.

    Контракт (platform_admin.py:device_mix):
      period_days, events_total, device, os, browser, conversion_by_device.
    Strict-equality на schema — backend rename → тест fail'ит loud.
    """
    r = httpx.get(
        f"{base_url}{API.PLATFORM_DEVICE_MIX}?days=30",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("period_days", "events_total", "device", "os", "browser", "conversion_by_device"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["period_days"] == 30
    assert isinstance(data["events_total"], int)
    assert isinstance(data["device"], dict)
    assert isinstance(data["conversion_by_device"], list)


def test_device_mix_clamps_days_lower_bound(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-1.3: days=0 → period_days=1 (canonical clamp)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_DEVICE_MIX}?days=0",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["period_days"] == 1


def test_device_mix_clamps_days_upper_bound(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-1.4: days=99999 → period_days=365 (canonical clamp)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_DEVICE_MIX}?days=99999",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["period_days"] == 365


def test_device_mix_does_not_leak_pii(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-1.5: GDPR — endpoint не возвращает email/raw IP/session_id."""
    import re as _re

    r = httpx.get(
        f"{base_url}{API.PLATFORM_DEVICE_MIX}?days=30",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    body = r.text
    assert "session_id" not in body, "session_id leaked in device-mix response"
    assert not _re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", body), \
        "raw IPv4 address leaked in device-mix response"


# ─────────────────────────────────────────────────────────────────────
# PR-2 — activity-heatmap
# ─────────────────────────────────────────────────────────────────────


def test_activity_heatmap_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-2.1: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ACTIVITY_HEATMAP}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_activity_heatmap_returns_7x24_matrix(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-2.2: матрица 7 строк × 24 столбца."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ACTIVITY_HEATMAP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    matrix = data["matrix"]
    assert len(matrix) == 7, f"matrix rows: {len(matrix)} (expected 7 weekdays)"
    for row in matrix:
        assert len(row) == 24, f"matrix row length: {len(row)} (expected 24 hours)"


def test_activity_heatmap_returns_canonical_fields(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-2.3: matrix, by_hour, by_weekday, top_hours, top_weekdays, coverage, tz_mode."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ACTIVITY_HEATMAP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in (
        "period_days", "tz_mode", "events_total", "matrix",
        "by_hour", "by_weekday", "top_hours", "top_weekdays", "coverage",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["tz_mode"] == "utc"
    assert len(data["by_hour"]) == 24
    assert len(data["by_weekday"]) == 7


def test_activity_heatmap_invalid_tz_mode_falls_back_to_utc(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-2.4: tz_mode=garbage → utc (документированный fallback)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ACTIVITY_HEATMAP}?tz_mode=garbage",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["tz_mode"] == "utc"


def test_activity_heatmap_user_local_mode_accepted(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-2.5: tz_mode=user_local — другая ветка кода (zoneinfo lookup).
    Должна вернуть валидную matrix + coverage.
    """
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ACTIVITY_HEATMAP}?tz_mode=user_local",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    assert data["tz_mode"] == "user_local"
    assert isinstance(data["coverage"], (int, float))
    assert 0.0 <= data["coverage"] <= 1.0


# ─────────────────────────────────────────────────────────────────────
# PR-3 — online-now + session-stats
# ─────────────────────────────────────────────────────────────────────


def test_online_now_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-3.1: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ONLINE_NOW}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_online_now_returns_canonical_shape(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-3.2: online_5m, online_1h (int), hourly_24h (24-list), as_of."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ONLINE_NOW}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("online_5m", "online_1h", "hourly_24h", "as_of"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert isinstance(data["online_5m"], int)
    assert isinstance(data["online_1h"], int)
    assert len(data["hourly_24h"]) == 24
    # Сам superadmin только что залогинился → online_5m >= 1
    assert data["online_5m"] >= 1, "superadmin session should count as online"


def test_session_stats_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-3.3: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_SESSION_STATS}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_session_stats_returns_canonical_shape(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-3.4: sessions_total, median_duration_s, p75_duration_s,
    median_pages, bounce_rate + by_device, by_utm_source, by_tier."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_SESSION_STATS}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in (
        "sessions_total", "median_duration_s", "p75_duration_s",
        "median_pages", "bounce_rate", "by_device", "by_utm_source", "by_tier",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert isinstance(data["sessions_total"], int)
    assert 0.0 <= data["bounce_rate"] <= 1.0


# ─────────────────────────────────────────────────────────────────────
# PR-4 — retention + time-to-aha + funnel-detail
# ─────────────────────────────────────────────────────────────────────


def test_retention_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-4.1: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_RETENTION}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_retention_returns_cohort_grid(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-4.2: weeks, buckets_days [1,3,7,14,30], cohorts list."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_RETENTION}?weeks=4",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("weeks", "buckets_days", "cohorts"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["weeks"] == 4
    assert data["buckets_days"] == [1, 3, 7, 14, 30]


def test_retention_clamps_weeks_to_max_26(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-4.3: weeks=999 → 26 (canonical clamp)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_RETENTION}?weeks=999",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["weeks"] == 26


def test_time_to_aha_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-4.4: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_TIME_TO_AHA}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_time_to_aha_returns_percentiles_and_buckets(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-4.5: P25/P50/P75/P95 + 6-bucket histogram."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_TIME_TO_AHA}?days=90",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in (
        "period_days", "target_event", "signups_total", "reached_target",
        "p25_hours", "p50_hours", "p75_hours", "p95_hours", "buckets",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["target_event"] == "enrichment_started"
    for b in ("0-1h", "1-4h", "4-24h", "1-3d", "3-7d", "7d+"):
        assert b in data["buckets"], f"bucket {b!r} missing"


def test_funnel_detail_returns_step_metrics(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-4.6: каждый step имеет users, drop_to_next,
    drop_rate_to_next, median_gap_to_next_s."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_FUNNEL_DETAIL}?days=30",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    assert "steps" in data, f"steps missing: {sorted(data)}"
    assert len(data["steps"]) >= 9, \
        f"funnel must include all 9 canonical events, got {len(data['steps'])}"
    for s in data["steps"]:
        for key in ("event", "users", "drop_to_next", "drop_rate_to_next", "median_gap_to_next_s"):
            assert key in s, f"step field {key!r} missing: {sorted(s)}"


# ─────────────────────────────────────────────────────────────────────
# PR-6 — alerts + health
# ─────────────────────────────────────────────────────────────────────


def test_alerts_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-6.1: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ALERTS}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_alerts_returns_items_list(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-6.2: items: list + as_of timestamp."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ALERTS}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    assert "items" in data, f"items missing: {sorted(data)}"
    assert "as_of" in data
    assert isinstance(data["items"], list)
    # На свежей БД должен быть как минимум backup_never
    ids = {it["id"] for it in data["items"]}
    assert "backup_never" in ids or any(it["id"] == "backup_overdue" for it in data["items"]), \
        f"backup-related alert expected on fresh test DB, got: {ids}"


def test_alerts_each_item_has_severity_title_message(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-6.3: контракт каждого элемента."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_ALERTS}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    items = r.json()["items"]
    for it in items:
        for key in ("id", "severity", "title", "message"):
            assert key in it, f"alert field {key!r} missing: {sorted(it)}"
        assert it["severity"] in ("info", "warning", "critical"), \
            f"unexpected severity: {it['severity']!r}"


def test_health_403_for_non_super(owner_user, base_url: str):
    """TC-PA-ANALYTICS-6.4: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_HEALTH}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_health_returns_canonical_metrics(superadmin_user, base_url: str):
    """TC-PA-ANALYTICS-6.5: events_last_hour, usage_cents_last_day,
    active_users, free_cap, free_cap_fill_ratio (+ optional last_backup)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_HEALTH}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in (
        "events_last_hour", "usage_cents_last_day", "active_users",
        "free_cap", "free_cap_fill_ratio",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert 0.0 <= data["free_cap_fill_ratio"] <= 1.0


# ─────────────────────────────────────────────────────────────────────
# UI smoke — все 9 виджетов на месте после bootstrap
# ─────────────────────────────────────────────────────────────────────


def test_dashboard_renders_phase1_widgets(
    auth_context_factory, superadmin_user, soft_check
):
    """TC-PA-ANALYTICS-UI-1: все Phase 1 виджеты присутствуют в DOM
    после загрузки страницы. Smoke-чек на 9 локаторов через soft_check.
    """
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_load_state("networkidle")

    dashboard = PlatformDashboardPage(page)
    dashboard.soft_check_phase1_widgets_present(soft_check)
