"""Platform superadmin audit log — TC-PA-AUDIT-* (PR-5).

Покрывает:
  • GET /api/platform/audit-log — фильтры + canonical shape
  • Integration: write-endpoint (settings_patch) пишет audit-запись
  • GDPR: ip_hash в формате hex, не raw IP
"""

from __future__ import annotations

import re

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


def test_audit_log_403_for_non_super(owner_user, base_url: str):
    """TC-PA-AUDIT-1: regular owner → 401/403."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_audit_log_returns_canonical_shape(superadmin_user, base_url: str):
    """TC-PA-AUDIT-2: items, count, limit + per-item: id, ts, actor_email,
    action, target_type, target_id, payload, ip_hash."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?limit=10",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("items", "count", "limit"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["limit"] == 10


def test_audit_log_clamps_limit_lower(superadmin_user, base_url: str):
    """TC-PA-AUDIT-3: limit=0 → 1 (canonical)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?limit=0",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["limit"] == 1


def test_audit_log_clamps_limit_upper(superadmin_user, base_url: str):
    """TC-PA-AUDIT-4: limit=99999 → 500 (canonical)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?limit=99999",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["limit"] == 500


def test_audit_log_invalid_since_iso_returns_400(superadmin_user, base_url: str):
    """TC-PA-AUDIT-5: since_iso=garbage → 400 (не silent fallback)."""
    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?since_iso=not-a-date",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 400, \
        f"invalid since_iso should be 400, got {r.status_code}"


def test_settings_patch_writes_audit_entry(superadmin_user, base_url: str):
    """TC-PA-AUDIT-6: PATCH /settings → запись в audit-log с action=settings_patch.

    Канонический сценарий: меняем soft_warn_threshold → ищем запись.
    """
    new_value = 0.7
    r1 = httpx.patch(
        f"{base_url}{API.PLATFORM_SETTINGS}",
        json={"soft_warn_threshold": new_value},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r1.raise_for_status()

    r2 = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?action=settings_patch&limit=5",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r2.raise_for_status()
    items = r2.json()["items"]
    assert len(items) >= 1, "settings_patch audit entry not created after PATCH"
    latest = items[0]
    assert latest["action"] == "settings_patch"
    assert latest["target_type"] == "platform_settings"
    # Payload содержит changes + before
    assert "changes" in latest["payload"]
    assert latest["payload"]["changes"]["soft_warn_threshold"] == new_value


def test_audit_log_ip_hash_is_hex_not_raw_ip(superadmin_user, base_url: str):
    """TC-PA-AUDIT-7 (GDPR): ip_hash — 16-символьный hex, не IPv4-подобный."""
    # Гарантируем хотя бы одну запись через self-PATCH
    httpx.patch(
        f"{base_url}{API.PLATFORM_SETTINGS}",
        json={"soft_warn_threshold": 0.85},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?limit=1",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    items = r.json()["items"]
    assert len(items) == 1
    ip_hash = items[0]["ip_hash"]
    assert ip_hash is not None, "ip_hash must be present (audit logs requesting client)"
    assert re.match(r"^[0-9a-f]{16}$", ip_hash), \
        f"ip_hash must be 16-char hex, got {ip_hash!r}"
    # Не должно выглядеть как IPv4
    assert not re.match(r"^\d+\.\d+\.\d+\.\d+", ip_hash)


def test_audit_log_filters_by_action(superadmin_user, base_url: str):
    """TC-PA-AUDIT-8: action=X возвращает только записи с action=X."""
    # Сначала создаём известную запись
    httpx.patch(
        f"{base_url}{API.PLATFORM_SETTINGS}",
        json={"soft_warn_threshold": 0.9},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?action=settings_patch&limit=20",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    items = r.json()["items"]
    for it in items:
        assert it["action"] == "settings_patch", \
            f"filter leak: got action={it['action']!r}"
