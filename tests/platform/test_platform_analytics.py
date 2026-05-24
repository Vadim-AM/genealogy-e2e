"""Platform superadmin analytics — TC-PA-ANALYTICS-* (Phase 1, PR-1..6)."""

from __future__ import annotations

import re
from http import HTTPStatus

import allure

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.platform_dashboard_page import PlatformDashboardPage
from src.texts import ErrMsg


@allure.title("Устройства: обычный владелец не имеет доступа (403)")
def test_device_mix_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-1.1: regular owner получает 401/403 на device-mix."""
    r = tenant_client(owner_user).get(routes.PLATFORM_DEVICE_MIX)
    expect_response(r, label="owner device-mix").status(HTTPStatus.FORBIDDEN)


@allure.title("Устройства: ответ содержит device, os, browser и конверсию")
def test_device_mix_returns_canonical_shape(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-1.2: суперадмин получает 200 + ожидаемые поля."""
    with step("действие: запрашиваем device-mix за 30 дней"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_DEVICE_MIX, params={"days": 30})
        expect_response(r, label="device-mix shape").status_ok()
        data = r.json()

    with step("проверка: все канонические поля присутствуют и типы верны"):
        for key in ("period_days", "events_total", "device", "os", "browser", "conversion_by_device"):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_equal(data["period_days"], 30, ErrMsg.response_field_wrong)
        should.be_instance(data["events_total"], int, ErrMsg.metric_type_wrong)
        should.be_instance(data["device"], dict, ErrMsg.metric_type_wrong)
        should.be_instance(data["conversion_by_device"], list, ErrMsg.metric_type_wrong)


@allure.title("Устройства: days=0 ограничивается снизу до 1")
def test_device_mix_clamps_days_lower_bound(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-1.3: days=0 → period_days=1 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(routes.PLATFORM_DEVICE_MIX, params={"days": 0})
    expect_response(r, label="device-mix days=0").status_ok().json_eq("period_days", 1)


@allure.title("Устройства: days=99999 ограничивается сверху до 365")
def test_device_mix_clamps_days_upper_bound(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-1.4: days=99999 → period_days=365 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(routes.PLATFORM_DEVICE_MIX, params={"days": 99999})
    expect_response(r, label="device-mix days=99999").status_ok().json_eq("period_days", 365)


@allure.title("Устройства GDPR: ответ не содержит session_id и IP")
def test_device_mix_does_not_leak_pii(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-1.5: GDPR — endpoint не возвращает email/raw IP/session_id."""
    with step("действие: запрашиваем device-mix"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_DEVICE_MIX, params={"days": 30})
        expect_response(r, label="device-mix PII check").status_ok()
        body = r.text

    with step("проверка: нет session_id и raw IP в ответе"):
        should.not_contain(body, "session_id", ErrMsg.session_id_leaked)
        should.be_false(re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", body), ErrMsg.ipv4_leaked)


@allure.title("Тепловая карта: обычный владелец не имеет доступа (403)")
def test_activity_heatmap_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-2.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_ACTIVITY_HEATMAP)
    expect_response(r, label="owner heatmap").status(HTTPStatus.FORBIDDEN)


@allure.title("Тепловая карта: матрица имеет размер 7 дней x 24 часа")
def test_activity_heatmap_returns_7x24_matrix(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-2.2: матрица 7 строк × 24 столбца."""
    with step("действие: запрашиваем тепловую карту"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_ACTIVITY_HEATMAP)
        expect_response(r, label="heatmap 7x24").status_ok()
        matrix = r.json()["matrix"]

    with step("проверка: матрица 7x24"):
        should.have_length(matrix, 7, ErrMsg.matrix_dimensions_wrong)
        for row in matrix:
            should.have_length(row, 24, ErrMsg.matrix_dimensions_wrong)


@allure.title("Тепловая карта: ответ содержит все канонические поля")
def test_activity_heatmap_returns_canonical_fields(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-2.3: matrix, by_hour, by_weekday, top_hours, top_weekdays, coverage, tz_mode."""
    with step("действие: запрашиваем тепловую карту"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_ACTIVITY_HEATMAP)
        expect_response(r, label="heatmap fields").status_ok()
        data = r.json()

    with step("проверка: все канонические поля присутствуют с верными размерами"):
        for key in (
            "period_days", "tz_mode", "events_total", "matrix",
            "by_hour", "by_weekday", "top_hours", "top_weekdays", "coverage",
        ):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_equal(data["tz_mode"], "utc", ErrMsg.response_field_wrong)
        should.have_length(data["by_hour"], 24, ErrMsg.count_mismatch)
        should.have_length(data["by_weekday"], 7, ErrMsg.count_mismatch)


@allure.title("Тепловая карта: некорректный tz_mode сбрасывается в utc")
def test_activity_heatmap_invalid_tz_mode_falls_back_to_utc(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-2.4: tz_mode=garbage → utc (документированный fallback)."""
    r = tenant_client(superadmin_user).get(
        routes.PLATFORM_ACTIVITY_HEATMAP, params={"tz_mode": "garbage"},
    )
    expect_response(r, label="heatmap tz_mode=garbage").status_ok().json_eq("tz_mode", "utc")


@allure.title("Тепловая карта: режим user_local возвращает валидные данные")
def test_activity_heatmap_user_local_mode_accepted(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-2.5: tz_mode=user_local — другая ветка кода (zoneinfo lookup)."""
    with step("действие: запрашиваем тепловую карту в режиме user_local"):
        r = tenant_client(superadmin_user).get(
            routes.PLATFORM_ACTIVITY_HEATMAP, params={"tz_mode": "user_local"},
        )
        expect_response(r, label="heatmap user_local").status_ok()
        data = r.json()

    with step("проверка: tz_mode=user_local и coverage в допустимом диапазоне"):
        should.be_equal(data["tz_mode"], "user_local", ErrMsg.response_field_wrong)
        should.be_true(isinstance(data["coverage"], (int, float)), ErrMsg.metric_type_wrong)
        should.be_true(0.0 <= data["coverage"] <= 1.0, ErrMsg.coverage_out_of_range)


@allure.title("Онлайн: обычный владелец не имеет доступа (403)")
def test_online_now_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-3.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_ONLINE_NOW)
    expect_response(r, label="owner online-now").status(HTTPStatus.FORBIDDEN)


@allure.title("Онлайн: суперадмин видит счётчики и себя в online_5m")
def test_online_now_returns_canonical_shape(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-3.2: online_5m, online_1h (int), hourly_24h (24-list), as_of."""
    with step("действие: запрашиваем online-now"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_ONLINE_NOW)
        expect_response(r, label="online-now shape").status_ok()
        data = r.json()

    with step("проверка: канонические поля, типы и superadmin в online_5m"):
        for key in ("online_5m", "online_1h", "hourly_24h", "as_of"):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_instance(data["online_5m"], int, ErrMsg.metric_type_wrong)
        should.be_instance(data["online_1h"], int, ErrMsg.metric_type_wrong)
        should.have_length(data["hourly_24h"], 24, ErrMsg.count_mismatch)
        should.greater_or_equal(data["online_5m"], 1, ErrMsg.metric_key_missing)


@allure.title("Статистика сессий: обычный владелец не имеет доступа (403)")
def test_session_stats_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-3.3: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_SESSION_STATS)
    expect_response(r, label="owner session-stats").status(HTTPStatus.FORBIDDEN)


@allure.title("Статистика сессий: ответ содержит медиану и bounce_rate")
def test_session_stats_returns_canonical_shape(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-3.4: sessions_total, median_duration_s, p75_duration_s,."""
    with step("действие: запрашиваем session-stats"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_SESSION_STATS)
        expect_response(r, label="session-stats shape").status_ok()
        data = r.json()

    with step("проверка: канонические поля, типы и bounce_rate в диапазоне"):
        for key in (
            "sessions_total", "median_duration_s", "p75_duration_s",
            "median_pages", "bounce_rate", "by_device", "by_utm_source", "by_tier",
        ):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_instance(data["sessions_total"], int, ErrMsg.metric_type_wrong)
        should.be_true(0.0 <= data["bounce_rate"] <= 1.0, ErrMsg.bounce_rate_out_of_range)


@allure.title("Ретеншен: обычный владелец не имеет доступа (403)")
def test_retention_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_RETENTION)
    expect_response(r, label="owner retention").status(HTTPStatus.FORBIDDEN)


@allure.title("Ретеншен: когортная таблица с бакетами [1,3,7,14,30]")
def test_retention_returns_cohort_grid(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.2: weeks, buckets_days [1,3,7,14,30], cohorts list."""
    with step("действие: запрашиваем retention за 4 недели"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_RETENTION, params={"weeks": 4})
        expect_response(r, label="retention cohort").status_ok()
        data = r.json()

    with step("проверка: weeks=4 и канонические buckets_days"):
        for key in ("weeks", "buckets_days", "cohorts"):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_equal(data["weeks"], 4, ErrMsg.response_field_wrong)
        should.be_equal(data["buckets_days"], [1, 3, 7, 14, 30], ErrMsg.retention_buckets_wrong)


@allure.title("Ретеншен: weeks=999 ограничивается сверху до 26")
def test_retention_clamps_weeks_to_max_26(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.3: weeks=999 → 26 (canonical clamp)."""
    r = tenant_client(superadmin_user).get(routes.PLATFORM_RETENTION, params={"weeks": 999})
    expect_response(r, label="retention weeks=999").status_ok().json_eq("weeks", 26)


@allure.title("Time-to-aha: обычный владелец не имеет доступа (403)")
def test_time_to_aha_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.4: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_TIME_TO_AHA)
    expect_response(r, label="owner time-to-aha").status(HTTPStatus.FORBIDDEN)


@allure.title("Time-to-aha: перцентили P25-P95 и 6 бакетов гистограммы")
def test_time_to_aha_returns_percentiles_and_buckets(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.5: P25/P50/P75/P95 + 6-bucket histogram."""
    with step("действие: запрашиваем time-to-aha за 90 дней"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_TIME_TO_AHA, params={"days": 90})
        expect_response(r, label="time-to-aha shape").status_ok()
        data = r.json()

    with step("проверка: перцентили, target_event и 6 бакетов"):
        for key in (
            "period_days", "target_event", "signups_total", "reached_target",
            "p25_hours", "p50_hours", "p75_hours", "p95_hours", "buckets",
        ):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_equal(data["target_event"], "enrichment_started", ErrMsg.response_field_wrong)
        for b in ("0-1h", "1-4h", "4-24h", "1-3d", "3-7d", "7d+"):
            should.be_in(b, data["buckets"], ErrMsg.metric_key_missing)


@allure.title("Воронка: каждый шаг содержит users и drop_rate")
def test_funnel_detail_returns_step_metrics(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-4.6: каждый step имеет users, drop_to_next,."""
    with step("действие: запрашиваем funnel-detail за 30 дней"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_FUNNEL_DETAIL, params={"days": 30})
        expect_response(r, label="funnel-detail").status_ok()
        data = r.json()

    with step("проверка: минимум 9 шагов с каноническими полями"):
        should.be_in("steps", data, ErrMsg.metric_key_missing)
        should.greater_or_equal(len(data["steps"]), 9, ErrMsg.funnel_steps_wrong)
        for s in data["steps"]:
            for key in ("event", "users", "drop_to_next", "drop_rate_to_next", "median_gap_to_next_s"):
                should.be_in(key, s, ErrMsg.metric_key_missing)


@allure.title("Алерты: обычный владелец не имеет доступа (403)")
def test_alerts_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-6.1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_ALERTS)
    expect_response(r, label="owner alerts").status(HTTPStatus.FORBIDDEN)


@allure.title("Алерты: на свежей БД есть алерт о бэкапе")
def test_alerts_returns_items_list(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-6.2: items: list + as_of timestamp."""
    with step("действие: запрашиваем алерты"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_ALERTS)
        expect_response(r, label="alerts list").status_ok()
        data = r.json()

    with step("проверка: items, as_of и backup-алерт на свежей БД"):
        should.be_in("items", data, ErrMsg.metric_key_missing)
        should.be_in("as_of", data, ErrMsg.metric_key_missing)
        should.be_instance(data["items"], list, ErrMsg.metric_type_wrong)
        ids = {it["id"] for it in data["items"]}
        backup_alerts = {"backup_never", "backup_overdue"}
        should.be_true(ids & backup_alerts, ErrMsg.backup_alert_missing)


@allure.title("Алерты: каждый элемент содержит severity, title, message")
def test_alerts_each_item_has_severity_title_message(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-6.3: контракт каждого элемента."""
    with step("действие: запрашиваем алерты"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_ALERTS)
        expect_response(r, label="alerts items").status_ok()
        items = r.json()["items"]

    with step("проверка: каждый элемент содержит id, severity, title, message"):
        for it in items:
            for key in ("id", "severity", "title", "message"):
                should.be_in(key, it, ErrMsg.metric_key_missing)
            should.be_in(it["severity"], ("info", "warning", "critical"), ErrMsg.alert_severity_wrong)


@allure.title("Здоровье платформы: обычный владелец не имеет доступа (403)")
def test_health_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-6.4: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_HEALTH)
    expect_response(r, label="owner health").status(HTTPStatus.FORBIDDEN)


@allure.title("Здоровье платформы: метрики нагрузки и free_cap_fill_ratio")
def test_health_returns_canonical_metrics(superadmin_user, tenant_client) -> None:
    """TC-PA-ANALYTICS-6.5: events_last_hour, usage_cents_last_day,."""
    with step("действие: запрашиваем health-метрики"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_HEALTH)
        expect_response(r, label="health metrics").status_ok()
        data = r.json()

    with step("проверка: канонические поля и free_cap_fill_ratio в диапазоне"):
        for key in (
            "events_last_hour", "usage_cents_last_day", "active_users",
            "free_cap", "free_cap_fill_ratio",
        ):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_true(0.0 <= data["free_cap_fill_ratio"] <= 1.0, ErrMsg.fill_ratio_out_of_range)


@allure.title("Дашборд: все 9 виджетов Phase 1 присутствуют в DOM")
def test_dashboard_renders_phase1_widgets(
    auth_context_factory, superadmin_user, soft_check
) -> None:
    """TC-PA-ANALYTICS-UI-1: все Phase 1 виджеты присутствуют в DOM."""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        page.wait_for_load_state("domcontentloaded")

    with step("проверка: все 9 виджетов Phase 1 присутствуют"):
        dashboard = PlatformDashboardPage(page)
        dashboard.soft_check_phase1_widgets_present(soft_check)
