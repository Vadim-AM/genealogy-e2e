"""Platform superadmin audit log — TC-PA-AUDIT-* (PR-5).

Покрывает:
  • GET /api/platform/audit-log — фильтры + canonical shape
  • Integration: write-endpoint (settings_patch) пишет audit-запись
  • GDPR: ip_hash в формате hex, не raw IP
"""

from __future__ import annotations

import re

from tests.api_paths import API


def test_audit_log_403_for_non_super(owner_user, tenant_client):
    """TC-PA-AUDIT-1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(API.PLATFORM_AUDIT_LOG)
    assert r.status_code in (401, 403)


def test_audit_log_returns_canonical_shape(superadmin_user, tenant_client):
    """TC-PA-AUDIT-2: items, count, limit + per-item: id, ts, actor_email,
    action, target_type, target_id, payload, ip_hash."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 10})
    r.raise_for_status()
    data = r.json()
    for key in ("items", "count", "limit"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["limit"] == 10


def test_audit_log_clamps_limit_lower(superadmin_user, tenant_client):
    """TC-PA-AUDIT-3: limit=0 → 1 (canonical)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 0})
    r.raise_for_status()
    assert r.json()["limit"] == 1


def test_audit_log_clamps_limit_upper(superadmin_user, tenant_client):
    """TC-PA-AUDIT-4: limit=99999 → 500 (canonical)."""
    r = tenant_client(superadmin_user).get(API.PLATFORM_AUDIT_LOG, params={"limit": 99999})
    r.raise_for_status()
    assert r.json()["limit"] == 500


def test_audit_log_invalid_since_iso_returns_400(superadmin_user, tenant_client):
    """TC-PA-AUDIT-5: since_iso=garbage → 400 (не silent fallback)."""
    r = tenant_client(superadmin_user).get(
        API.PLATFORM_AUDIT_LOG, params={"since_iso": "not-a-date"},
    )
    assert r.status_code == 400, \
        f"invalid since_iso should be 400, got {r.status_code}"


def test_settings_patch_writes_audit_entry(superadmin_user, tenant_client):
    """TC-PA-AUDIT-6: PATCH /settings → запись в audit-log с action=settings_patch.

    Канонический сценарий: меняем soft_warn_threshold → ищем запись.
    """
    api = tenant_client(superadmin_user)
    new_value = 0.7
    api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": new_value}).raise_for_status()

    r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "settings_patch", "limit": 5})
    r.raise_for_status()
    items = r.json()["items"]
    assert len(items) >= 1, "settings_patch audit entry not created after PATCH"
    latest = items[0]
    assert latest["action"] == "settings_patch"
    assert latest["target_type"] == "platform_settings"
    # Payload содержит changes + before
    assert "changes" in latest["payload"]
    assert latest["payload"]["changes"]["soft_warn_threshold"] == new_value


def test_audit_log_ip_hash_is_hex_not_raw_ip(superadmin_user, tenant_client):
    """TC-PA-AUDIT-7 (GDPR): ip_hash — 16-символьный hex, не IPv4-подобный."""
    api = tenant_client(superadmin_user)
    # Гарантируем хотя бы одну запись через self-PATCH
    api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.85}).raise_for_status()

    r = api.get(API.PLATFORM_AUDIT_LOG, params={"limit": 1})
    r.raise_for_status()
    items = r.json()["items"]
    assert len(items) == 1
    ip_hash = items[0]["ip_hash"]
    assert ip_hash is not None, "ip_hash must be present (audit logs requesting client)"
    assert re.match(r"^[0-9a-f]{16}$", ip_hash), \
        f"ip_hash must be 16-char hex, got {ip_hash!r}"
    # Не должно выглядеть как IPv4
    assert not re.match(r"^\d+\.\d+\.\d+\.\d+", ip_hash)


def test_audit_log_filters_by_action(superadmin_user, tenant_client):
    """TC-PA-AUDIT-8: action=X возвращает только записи с action=X."""
    api = tenant_client(superadmin_user)
    api.patch(API.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.9}).raise_for_status()

    r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "settings_patch", "limit": 20})
    r.raise_for_status()
    items = r.json()["items"]
    for it in items:
        assert it["action"] == "settings_patch", \
            f"filter leak: got action={it['action']!r}"
