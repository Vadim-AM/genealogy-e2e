"""Platform superadmin audit log — TC-PA-AUDIT-* (PR-5).

Покрывает:
  • GET /api/platform/audit-log — фильтры + canonical shape
  • Integration: write-endpoint (settings_patch) пишет audit-запись
  • GDPR: ip_hash в формате hex, не raw IP
"""

from __future__ import annotations

import re

import allure

from tests.api_paths import API
from tests.response import expect_response
from tests.step import step


@allure.title("Аудит: журнал недоступен обычному владельцу")
def test_audit_log_403_for_non_super(owner_user, tenant_client):
    """TC-PA-AUDIT-1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_AUDIT_LOG)
    expect_response(r, label="owner audit-log").status(403)


@allure.title("Аудит: ответ содержит items, count и limit")
def test_audit_log_returns_canonical_shape(superadmin_user, tenant_client):
    """TC-PA-AUDIT-2: items, count, limit + per-item: id, ts, actor_email,
    action, target_type, target_id, payload, ip_hash."""
    with step("действие: запрашиваем audit-log с limit=10"):
        r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 10})
        expect_response(r, label="audit-log shape").status_ok()
        data = r.json()

    with step("проверка: items, count, limit присутствуют и limit=10"):
        for key in ("items", "count", "limit"):
            assert key in data, f"field {key!r} missing: {sorted(data)}"
        assert data["limit"] == 10, \
            f"default limit should be 10, got {data.get('limit')}"


@allure.title("Аудит: limit=0 ограничивается снизу до 1")
def test_audit_log_clamps_limit_lower(superadmin_user, tenant_client):
    """TC-PA-AUDIT-3: limit=0 → 1 (canonical)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 0})
    expect_response(r, label="audit-log limit=0").status_ok().json_eq("limit", 1)


@allure.title("Аудит: limit=99999 ограничивается сверху до 500")
def test_audit_log_clamps_limit_upper(superadmin_user, tenant_client):
    """TC-PA-AUDIT-4: limit=99999 → 500 (canonical)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 99999})
    expect_response(r, label="audit-log limit=99999").status_ok().json_eq("limit", 500)


@allure.title("Аудит: некорректная дата since_iso возвращает 400")
def test_audit_log_invalid_since_iso_returns_400(superadmin_user, tenant_client):
    """TC-PA-AUDIT-5: since_iso=garbage → 400 (не silent fallback)."""
    with step("действие: запрашиваем audit-log с невалидной датой"):
        r = tenant_client(superadmin_user).get(
            API.PLATFORM_AUDIT_LOG, params={"since_iso": "not-a-date"},
        )

    with step("проверка: 400 — не silent fallback"):
        expect_response(r, label="audit-log invalid since_iso").status(400)


@allure.title("Аудит: изменение настроек создаёт запись settings_patch")
def test_settings_patch_writes_audit_entry(superadmin_user, tenant_client):
    """TC-PA-AUDIT-6: PATCH /settings → запись в audit-log с action=settings_patch.

    Канонический сценарий: меняем soft_warn_threshold → ищем запись.
    """
    api = tenant_client(superadmin_user)
    new_value = 0.7

    with step("действие: патчим soft_warn_threshold"):
        api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": new_value}).raise_for_status()

    with step("действие: запрашиваем audit-log по action=settings_patch"):
        r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "settings_patch", "limit": 5})
        expect_response(r, label="audit-log settings_patch").status_ok()
        items = r.json()["items"]

    with step("проверка: audit-запись содержит корректные action, target_type и payload"):
        assert len(items) >= 1, "settings_patch audit entry not created after PATCH"
        latest = items[0]
        assert latest["action"] == "settings_patch", \
            f"latest audit action: expected 'settings_patch', got {latest.get('action')!r}"
        assert latest["target_type"] == "platform_settings", \
            f"target_type: expected 'platform_settings', got {latest.get('target_type')!r}"
        # Payload содержит changes + before
        assert "changes" in latest["payload"], \
            f"audit payload must contain 'changes': {sorted(latest.get('payload', {}))}"
        assert latest["payload"]["changes"]["soft_warn_threshold"] == new_value, \
            f"soft_warn_threshold not recorded: {latest['payload'].get('changes')}"


@allure.title("Аудит GDPR: ip_hash — hex-хеш, а не сырой IP-адрес")
def test_audit_log_ip_hash_is_hex_not_raw_ip(superadmin_user, tenant_client):
    """TC-PA-AUDIT-7 (GDPR): ip_hash — 16-символьный hex, не IPv4-подобный."""
    api = tenant_client(superadmin_user)

    with step("подготовка: создаём audit-запись через self-PATCH"):
        api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.85}).raise_for_status()

    with step("действие: запрашиваем последнюю audit-запись"):
        r = api.get(API.PLATFORM_AUDIT_LOG, params={"limit": 1})
        expect_response(r, label="audit-log ip_hash").status_ok()
        items = r.json()["items"]

    with step("проверка: ip_hash — 16-символьный hex, не IPv4"):
        assert len(items) == 1, (
            f"expected exactly 1 audit item with limit=1, got {len(items)}"
        )
        ip_hash = items[0]["ip_hash"]
        assert ip_hash is not None, "ip_hash must be present (audit logs requesting client)"
        assert re.match(r"^[0-9a-f]{16}$", ip_hash), \
            f"ip_hash must be 16-char hex, got {ip_hash!r}"
        # Не должно выглядеть как IPv4
        assert not re.match(r"^\d+\.\d+\.\d+\.\d+", ip_hash), (
            f"ip_hash looks like raw IPv4 (GDPR violation): {ip_hash!r}"
        )


@allure.title("Аудит: фильтр по action возвращает только нужные записи")
def test_audit_log_filters_by_action(superadmin_user, tenant_client):
    """TC-PA-AUDIT-8: action=X возвращает только записи с action=X."""
    api = tenant_client(superadmin_user)

    with step("подготовка: создаём settings_patch запись"):
        api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.9}).raise_for_status()

    with step("проверка: фильтр по action возвращает только settings_patch"):
        r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "settings_patch", "limit": 20})
        expect_response(r, label="audit-log filter by action").status_ok()
        items = r.json()["items"]
        for it in items:
            assert it["action"] == "settings_patch", \
                f"filter leak: got action={it['action']!r}"
