"""Platform step-up auth + CSP — TC-PA-STEPUP-* (PR-10)."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import pyotp

from api import mfa_api, platform_api, routes
from assertions.base import should
from config.constants import make_email
from fixtures.users import setup_and_verify_mfa
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Step-up: критичное действие без подтверждения — 403")
def test_grant_license_403_step_up_required_without_step_up(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-1: critical endpoint требует step_up_verified, иначе 403."""
    with step("подготовка: setup MFA без step-up"):
        api = tenant_client(superadmin_user)
        setup_and_verify_mfa(api)

    with step("проверка: grant-license без step-up отклоняется 403"):
        r = api.post(
            routes.PLATFORM_FREE_LICENSE_GRANT,
            json={"email": make_email("stepup-target")},
        )
        expect_response(r, label="grant without step-up").status(HTTPStatus.FORBIDDEN)
        should.contain(r.text, "step_up_required", ErrMsg.step_up_required_missing)


@allure.title("Step-up: TOTP-подтверждение разблокирует выдачу лицензии")
def test_step_up_with_valid_totp_unlocks_critical_action(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-2: step-up TOTP → grant-license проходит."""
    with step("подготовка: setup MFA и step-up через TOTP"):
        api = tenant_client(superadmin_user)
        secret = setup_and_verify_mfa(api)
        code = pyotp.TOTP(secret).now()
        r1 = api.post(routes.MFA_STEP_UP, json={"method": "totp", "code": code})
        expect_response(r1, label="step-up TOTP").status_ok().json_eq("status", "ok")

    with step("проверка: grant-license после step-up проходит"):
        r2 = api.post(
            routes.PLATFORM_FREE_LICENSE_GRANT,
            json={"email": make_email("stepup-grant-ok")},
        )
        expect_response(r2, label="grant after step-up").status_ok().json_eq("status", "granted")


@allure.title("Step-up: неверный TOTP-код отклоняется (401)")
def test_step_up_invalid_totp_401(superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]) -> None:
    """TC-PA-STEPUP-3: неверный TOTP в step-up → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("проверка: неверный TOTP в step-up — 401"):
        r = api.post(routes.MFA_STEP_UP, json={"method": "totp", "code": "000000"})
        expect_response(r, label="step-up invalid TOTP").status(HTTPStatus.UNAUTHORIZED)


@allure.title("Step-up: неизвестный метод подтверждения — 400")
def test_step_up_unknown_method_400(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-4: method=garbage → 400 (unknown_method)."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("проверка: неизвестный метод — 400"):
        r = api.post(routes.MFA_STEP_UP, json={"method": "garbage", "code": "000000"})
        expect_response(r, label="step-up unknown method").status(HTTPStatus.BAD_REQUEST)


@allure.title("Step-up: успешное подтверждение записывается в аудит")
def test_step_up_writes_audit_event(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-5: успешный step-up пишет audit-запись step_up_verified."""
    with step("подготовка: setup MFA и step-up"):
        api = tenant_client(superadmin_user)
        secret = setup_and_verify_mfa(api)
        code = pyotp.TOTP(secret).now()
        expect_response(
            api.post(routes.MFA_STEP_UP, json={"method": "totp", "code": code}),
            label="MFA step-up",
        ).status_ok()

    with step("действие: запрашиваем audit-log"):
        audit = platform_api.get_audit_log(api, action="step_up_verified", limit=5)

    with step("проверка: запись step_up_verified с method=totp"):
        should.greater_or_equal(len(audit.items), 1, ErrMsg.step_up_audit_missing)
        first = audit.items[0]
        should.be_equal(first.action, "step_up_verified", ErrMsg.audit_action_wrong)
        payload = first.model_extra.get("payload", {})
        should.be_equal(payload.get("method"), "totp", ErrMsg.step_up_method_wrong)


@allure.title("Step-up: резервный код работает как метод подтверждения")
def test_recovery_redeem_works_as_step_up_method(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-6: method=recovery с валидным кодом → 200."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        recovery = mfa_api.regenerate_recovery_codes(api)
        codes = recovery.codes

    with step("проверка: step-up через recovery-код — 200"):
        r = api.post(routes.MFA_STEP_UP, json={"method": "recovery", "code": codes[0]})
        expect_response(r, label="step-up recovery").status_ok().json_eq("status", "ok")


@allure.title("CSP: дашборд возвращает Content-Security-Policy заголовок")
def test_dashboard_returns_csp_header(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-7: GET /platform/dashboard → Content-Security-Policy установлен."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()
        csp = r.headers.get("content-security-policy", "")

    with step("проверка: CSP содержит канонические директивы"):
        should.be_true(csp, ErrMsg.csp_missing)
        for directive in (
            "default-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
        ):
            should.contain(csp, directive, ErrMsg.csp_directive_missing)


@allure.title("Безопасность: X-Frame-Options = DENY на дашборде")
def test_dashboard_returns_x_frame_options_deny(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-8: X-Frame-Options: DENY (anti-clickjacking)."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()

    with step("проверка: X-Frame-Options = DENY"):
        should.be_equal(r.headers.get("x-frame-options", "").upper(), "DENY", ErrMsg.security_header_wrong)


@allure.title("Безопасность: Referrer-Policy = no-referrer на дашборде")
def test_dashboard_returns_referrer_policy_no_referrer(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-9: Referrer-Policy: no-referrer."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()

    with step("проверка: Referrer-Policy = no-referrer"):
        should.be_equal(r.headers.get("referrer-policy", "").lower(), "no-referrer", ErrMsg.security_header_wrong)


@allure.title("Безопасность: Permissions-Policy разрешает WebAuthn")
def test_dashboard_returns_permissions_policy_for_webauthn(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-STEPUP-10: Permissions-Policy разрешает publickey-credentials."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()
        pp = r.headers.get("permissions-policy", "")

    with step("проверка: publickey-credentials-get и -create разрешены"):
        should.contain(pp, "publickey-credentials-get", ErrMsg.permissions_policy_wrong)
        should.contain(pp, "publickey-credentials-create", ErrMsg.permissions_policy_wrong)
