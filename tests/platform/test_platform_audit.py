"""Platform superadmin audit log — TC-PA-AUDIT-* (PR-5)."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import platform_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Аудит: журнал недоступен обычному владельцу")
def test_audit_log_403_for_non_super(owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]) -> None:
    """TC-PA-AUDIT-1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.PLATFORM_AUDIT_LOG)
    expect_response(r, label="owner audit-log").status(HTTPStatus.FORBIDDEN)


@allure.title("Аудит: ответ содержит items, count и limit")
def test_audit_log_returns_canonical_shape(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-2: items, count, limit + per-item: id, ts, actor_email,."""
    with step("действие: запрашиваем audit-log с limit=10"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_AUDIT_LOG, params={"limit": 10})
        data = expect_response(r, label="audit-log shape").status_ok().data

    with step("проверка: items, count, limit присутствуют и limit=10"):
        for key in ("items", "count", "limit"):
            should.be_in(key, data, ErrMsg.metric_key_missing)
        should.be_equal(data["limit"], 10, ErrMsg.audit_limit_wrong)


@allure.title("Аудит: limit=0 ограничивается снизу до 1")
def test_audit_log_clamps_limit_lower(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-3: limit=0 → 1 (canonical)."""
    r = tenant_client(superadmin_user).get(routes.PLATFORM_AUDIT_LOG, params={"limit": 0})
    expect_response(r, label="audit-log limit=0").status_ok().json_eq("limit", 1)


@allure.title("Аудит: limit=99999 ограничивается сверху до 500")
def test_audit_log_clamps_limit_upper(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-4: limit=99999 → 500 (canonical)."""
    r = tenant_client(superadmin_user).get(routes.PLATFORM_AUDIT_LOG, params={"limit": 99999})
    expect_response(r, label="audit-log limit=99999").status_ok().json_eq("limit", 500)


@allure.title("Аудит: некорректная дата since_iso возвращает 400")
def test_audit_log_invalid_since_iso_returns_400(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-5: since_iso=garbage → 400 (не silent fallback)."""
    with step("действие: запрашиваем audit-log с невалидной датой"):
        r = tenant_client(superadmin_user).get(
            routes.PLATFORM_AUDIT_LOG,
            params={"since_iso": "not-a-date"},
        )

    with step("проверка: 400 — не silent fallback"):
        expect_response(r, label="audit-log invalid since_iso").status(HTTPStatus.BAD_REQUEST)


@allure.title("Аудит: изменение настроек создаёт запись settings_patch")
def test_settings_patch_writes_audit_entry(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-6: PATCH /settings → запись в audit-log с action=settings_patch."""
    api = tenant_client(superadmin_user)
    new_value = 0.7

    with step("действие: патчим soft_warn_threshold"):
        expect_response(
            api.patch(routes.PLATFORM_SETTINGS, json={"soft_warn_threshold": new_value}),
            label="patch settings",
        ).status_ok()

    with step("действие: запрашиваем audit-log по action=settings_patch"):
        audit = platform_api.get_audit_log(api, action="settings_patch", limit=5)

    with step("проверка: audit-запись содержит корректные action, target_type и payload"):
        should.greater_or_equal(len(audit.items), 1, ErrMsg.audit_entry_missing)
        latest = audit.items[0]
        should.be_equal(latest.action, "settings_patch", ErrMsg.audit_action_wrong)
        target_type = (latest.model_extra or {}).get("target_type")
        should.be_equal(target_type, "platform_settings", ErrMsg.audit_action_wrong)
        # Payload содержит changes + before
        payload = (latest.model_extra or {}).get("payload", {})
        should.be_in("changes", payload, ErrMsg.audit_payload_wrong)
        should.be_equal(payload["changes"]["soft_warn_threshold"], new_value, ErrMsg.audit_payload_wrong)


@allure.title("Аудит GDPR: ip_hash — hex-хеш, а не сырой IP-адрес")
def test_audit_log_ip_hash_is_hex_not_raw_ip(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-7 (GDPR): ip_hash — 16-символьный hex, не IPv4-подобный."""
    api = tenant_client(superadmin_user)

    with step("подготовка: создаём audit-запись через self-PATCH"):
        expect_response(
            api.patch(routes.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.85}),
            label="patch settings",
        ).status_ok()

    with step("действие: запрашиваем последнюю audit-запись"):
        audit = platform_api.get_audit_log(api, limit=1)

    with step("проверка: ip_hash — 16-символьный hex, не IPv4"):
        should.have_length(audit.items, 1, ErrMsg.audit_entry_missing)
        ip_hash = should.not_none(audit.items[0].ip_hash, ErrMsg.audit_ip_hash_wrong)
        should.be_true(re.match(r"^[0-9a-f]{16}$", ip_hash), ErrMsg.audit_ip_hash_wrong)
        # Не должно выглядеть как IPv4
        should.be_false(re.match(r"^\d+\.\d+\.\d+\.\d+", ip_hash), ErrMsg.audit_ip_raw)


@allure.title("Аудит: фильтр по action возвращает только нужные записи")
def test_audit_log_filters_by_action(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-AUDIT-8: action=X возвращает только записи с action=X."""
    api = tenant_client(superadmin_user)

    with step("подготовка: создаём settings_patch запись"):
        expect_response(
            api.patch(routes.PLATFORM_SETTINGS, json={"soft_warn_threshold": 0.9}),
            label="patch settings",
        ).status_ok()

    with step("проверка: фильтр по action возвращает только settings_patch"):
        audit = platform_api.get_audit_log(api, action="settings_patch", limit=20)
        for it in audit.items:
            should.be_equal(it.action, "settings_patch", ErrMsg.audit_filter_leak)
