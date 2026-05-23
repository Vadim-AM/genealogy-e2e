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

import re

from tests.api_paths import API
from tests.pages.platform_dashboard_page import PlatformDashboardPage


# ─────────────────────────────────────────────────────────────────────
# PR-1 — device-mix
# ─────────────────────────────────────────────────────────────────────


def test_device_mix_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-1.1: regular owner получает 401/403 на device-mix."""
    r = tenant_client(owner_user).get(API.PLATFORM_DEVICE_MIX)
    assert r.status_code == 403, \
        f"non-superadmin reached device-mix: {r.status_code} {r.text[:200]}"


def test_device_mix_returns_canonical_shape(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-1.2: суперадмин получает 200 + ожидаемые поля.

    Контракт (platform_admin.py:device_mix):
      period_days, events_total, device, os, browser, conversion_by_device.
    Strict-equality на schema — backend rename → тест fail'ит loud.
    """
    r = tenant_client(superadmin_user).get(API.PLATFORM_DEVICE_MIX, params={"days": 30})
    r.raise_for_status()
    data = r.json()
    for key in ("period_days", "events_total", "device", "os", "browser", "conversion_by_device"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["period_days"] == 30, \
        f"period_days: expected 30, got {data.get('period_days')}"
    assert isinstance(data["events_total"], int), \
        f"events_total must be int, got {type(data.get('events_total')).__name__}"
    assert isinstance(data["device"], dict), \
        f"device must be dict, got {type(data.get('device')).__name__}"
    assert isinstance(data["conversion_by_device"], list), \
        f"conversion_by_device must be list, got {type(data.get('conversion_by_device')).__name__}"


def test_device_mix_clamps_days_lower_bound(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-1.3: days=0 → period_days=1 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_DEVICE_MIX, params={"days": 0})
    r.raise_for_status()
    assert r.json()["period_days"] == 1, \
        f"period_days: expected 1 (clamped), got {r.json()['period_days']}"


def test_device_mix_clamps_days_upper_bound(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-1.4: days=99999 → period_days=365 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_DEVICE_MIX, params={"days": 99999})
    r.raise_for_status()
    assert r.json()["period_days"] == 365, \
        f"period_days: expected 365 (clamped), got {r.json()['period_days']}"


def test_device_mix_does_not_leak_pii(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-1.5: GDPR — endpoint не возвращает email/raw IP/session_id."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_DEVICE_MIX, params={"days": 30})
    r.raise_for_status()
    body = r.text
    assert "session_id" not in body, "session_id leaked in device-mix response"
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", body), \
        "raw IPv4 address leaked in device-mix response"


# ─────────────────────────────────────────────────────────────────────
# PR-2 — activity-heatmap
# ─────────────────────────────────────────────────────────────────────


def test_activity_heatmap_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-2.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_ACTIVITY_HEATMAP)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_activity_heatmap_returns_7x24_matrix(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-2.2: матрица 7 строк × 24 столбца."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_ACTIVITY_HEATMAP)
    r.raise_for_status()
    matrix = r.json()["matrix"]
    assert len(matrix) == 7, f"matrix rows: {len(matrix)} (expected 7 weekdays)"
    for row in matrix:
        assert len(row) == 24, f"matrix row length: {len(row)} (expected 24 hours)"


def test_activity_heatmap_returns_canonical_fields(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-2.3: matrix, by_hour, by_weekday, top_hours, top_weekdays, coverage, tz_mode."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_ACTIVITY_HEATMAP)
    r.raise_for_status()
    data = r.json()
    for key in (
        "period_days", "tz_mode", "events_total", "matrix",
        "by_hour", "by_weekday", "top_hours", "top_weekdays", "coverage",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["tz_mode"] == "utc", \
        f"tz_mode: expected 'utc', got {data['tz_mode']!r}"
    assert len(data["by_hour"]) == 24, \
        f"by_hour: expected 24 entries, got {len(data['by_hour'])}"
    assert len(data["by_weekday"]) == 7, \
        f"by_weekday: expected 7 entries, got {len(data['by_weekday'])}"


def test_activity_heatmap_invalid_tz_mode_falls_back_to_utc(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-2.4: tz_mode=garbage → utc (документированный fallback)."""
    r = tenant_client(superadmin_user).get(
        API.PLATFORM_ACTIVITY_HEATMAP, params={"tz_mode": "garbage"},
    )
    r.raise_for_status()
    assert r.json()["tz_mode"] == "utc", \
        f"tz_mode: expected 'utc' fallback, got {r.json()['tz_mode']!r}"


def test_activity_heatmap_user_local_mode_accepted(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-2.5: tz_mode=user_local — другая ветка кода (zoneinfo lookup).
    Должна вернуть валидную matrix + coverage.
    """
    r = tenant_client(superadmin_user).get(
        API.PLATFORM_ACTIVITY_HEATMAP, params={"tz_mode": "user_local"},
    )
    r.raise_for_status()
    data = r.json()
    assert data["tz_mode"] == "user_local", \
        f"tz_mode: expected 'user_local', got {data['tz_mode']!r}"
    assert isinstance(data["coverage"], (int, float)), \
        f"coverage must be int or float, got {type(data['coverage']).__name__}"
    assert 0.0 <= data["coverage"] <= 1.0, \
        f"coverage must be in [0.0, 1.0], got {data['coverage']}"


# ─────────────────────────────────────────────────────────────────────
# PR-3 — online-now + session-stats
# ─────────────────────────────────────────────────────────────────────


def test_online_now_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-3.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_ONLINE_NOW)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_online_now_returns_canonical_shape(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-3.2: online_5m, online_1h (int), hourly_24h (24-list), as_of."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_ONLINE_NOW)
    r.raise_for_status()
    data = r.json()
    for key in ("online_5m", "online_1h", "hourly_24h", "as_of"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert isinstance(data["online_5m"], int), \
        f"online_5m must be int, got {type(data['online_5m']).__name__}"
    assert isinstance(data["online_1h"], int), \
        f"online_1h must be int, got {type(data['online_1h']).__name__}"
    assert len(data["hourly_24h"]) == 24, \
        f"hourly_24h: expected 24 entries, got {len(data['hourly_24h'])}"
    # Сам superadmin только что залогинился → online_5m >= 1
    assert data["online_5m"] >= 1, "superadmin session should count as online"


def test_session_stats_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-3.3: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_SESSION_STATS)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_session_stats_returns_canonical_shape(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-3.4: sessions_total, median_duration_s, p75_duration_s,
    median_pages, bounce_rate + by_device, by_utm_source, by_tier."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_SESSION_STATS)
    r.raise_for_status()
    data = r.json()
    for key in (
        "sessions_total", "median_duration_s", "p75_duration_s",
        "median_pages", "bounce_rate", "by_device", "by_utm_source", "by_tier",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert isinstance(data["sessions_total"], int), \
        f"sessions_total must be int, got {type(data['sessions_total']).__name__}"
    assert 0.0 <= data["bounce_rate"] <= 1.0, \
        f"bounce_rate must be in [0.0, 1.0], got {data['bounce_rate']}"


# ─────────────────────────────────────────────────────────────────────
# PR-4 — retention + time-to-aha + funnel-detail
# ─────────────────────────────────────────────────────────────────────


def test_retention_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-4.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_RETENTION)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_retention_returns_cohort_grid(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-4.2: weeks, buckets_days [1,3,7,14,30], cohorts list."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_RETENTION, params={"weeks": 4})
    r.raise_for_status()
    data = r.json()
    for key in ("weeks", "buckets_days", "cohorts"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["weeks"] == 4, \
        f"weeks: expected 4, got {data['weeks']}"
    assert data["buckets_days"] == [1, 3, 7, 14, 30], \
        f"buckets_days: expected [1, 3, 7, 14, 30], got {data['buckets_days']}"


def test_retention_clamps_weeks_to_max_26(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-4.3: weeks=999 → 26 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_RETENTION, params={"weeks": 999})
    r.raise_for_status()
    assert r.json()["weeks"] == 26, \
        f"weeks: expected 26 (clamped), got {r.json()['weeks']}"


def test_time_to_aha_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-4.4: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_TIME_TO_AHA)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_time_to_aha_returns_percentiles_and_buckets(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-4.5: P25/P50/P75/P95 + 6-bucket histogram."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_TIME_TO_AHA, params={"days": 90})
    r.raise_for_status()
    data = r.json()
    for key in (
        "period_days", "target_event", "signups_total", "reached_target",
        "p25_hours", "p50_hours", "p75_hours", "p95_hours", "buckets",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["target_event"] == "enrichment_started", \
        f"target_event: expected 'enrichment_started', got {data['target_event']!r}"
    for b in ("0-1h", "1-4h", "4-24h", "1-3d", "3-7d", "7d+"):
        assert b in data["buckets"], f"bucket {b!r} missing"


def test_funnel_detail_returns_step_metrics(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-4.6: каждый step имеет users, drop_to_next,
    drop_rate_to_next, median_gap_to_next_s."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_FUNNEL_DETAIL, params={"days": 30})
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


def test_alerts_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-6.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_ALERTS)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_alerts_returns_items_list(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-6.2: items: list + as_of timestamp."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_ALERTS)
    r.raise_for_status()
    data = r.json()
    assert "items" in data, f"items missing: {sorted(data)}"
    assert "as_of" in data, \
        f"as_of missing from response: {sorted(data)}"
    assert isinstance(data["items"], list), \
        f"items must be list, got {type(data['items']).__name__}"
    # На свежей БД должен быть один из backup-related alert'ов
    # (`backup_never` если ни одного бэкапа не было, `backup_overdue` если
    # старее threshold). Принимаем оба как канонические — backend выбирает
    # один в зависимости от состояния, не оба сразу.
    ids = {it["id"] for it in data["items"]}
    backup_alerts = {"backup_never", "backup_overdue"}
    assert ids & backup_alerts, \
        f"expected one of {backup_alerts} on fresh test DB, got: {ids}"


def test_alerts_each_item_has_severity_title_message(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-6.3: контракт каждого элемента."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_ALERTS)
    r.raise_for_status()
    items = r.json()["items"]
    for it in items:
        for key in ("id", "severity", "title", "message"):
            assert key in it, f"alert field {key!r} missing: {sorted(it)}"
        assert it["severity"] in ("info", "warning", "critical"), \
            f"unexpected severity: {it['severity']!r}"


def test_health_403_for_non_super(owner_user, tenant_client):
    """TC-PA-ANALYTICS-6.4: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_HEALTH)
    assert r.status_code == 403, \
        f"expected 403, got {r.status_code}"


def test_health_returns_canonical_metrics(superadmin_user, tenant_client):
    """TC-PA-ANALYTICS-6.5: events_last_hour, usage_cents_last_day,
    active_users, free_cap, free_cap_fill_ratio (+ optional last_backup)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_HEALTH)
    r.raise_for_status()
    data = r.json()
    for key in (
        "events_last_hour", "usage_cents_last_day", "active_users",
        "free_cap", "free_cap_fill_ratio",
    ):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert 0.0 <= data["free_cap_fill_ratio"] <= 1.0, \
        f"free_cap_fill_ratio must be in [0.0, 1.0], got {data['free_cap_fill_ratio']}"


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
    page.wait_for_load_state("domcontentloaded")

    dashboard = PlatformDashboardPage(page)
    dashboard.soft_check_phase1_widgets_present(soft_check)
