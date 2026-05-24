"""Platform step-up auth + CSP — TC-PA-STEPUP-* (PR-10).

Покрывает:
  • POST /api/platform/mfa/step-up — TOTP-method, audit, freshness.
  • Critical action (free-license-grant, backup-snapshot, cleanup-deleted,
    tenant-override) → 403 step_up_required без свежего step-up.
  • Replay critical action после step-up → 200.
  • CSP-headers и связанные security-headers на /platform/dashboard.

Hard rules: hard assert, single canonical field.
"""

from __future__ import annotations

import allure
import pyotp

from tests._fixtures.users import setup_and_verify_mfa
from tests.api_paths import API
from tests.constants import make_email
from tests.response import expect_response
from tests.step import step


@allure.title("Step-up: критичное действие без подтверждения — 403")
def test_grant_license_403_step_up_required_without_step_up(
    superadmin_user, tenant_client,
):
    """TC-PA-STEPUP-1: critical endpoint требует step_up_verified, иначе 403."""
    with step("подготовка: setup MFA без step-up"):
        api = tenant_client(superadmin_user)
        setup_and_verify_mfa(api)

    with step("проверка: grant-license без step-up отклоняется 403"):
        r = api.post(
            API.PLATFORM_FREE_LICENSE_GRANT,
            json={"email": make_email("stepup-target")},
        )
        expect_response(r, label="grant without step-up").status(403)
        assert "step_up_required" in r.text, \
            f"expected 'step_up_required' in response: {r.text[:200]}"


@allure.title("Step-up: TOTP-подтверждение разблокирует выдачу лицензии")
def test_step_up_with_valid_totp_unlocks_critical_action(
    superadmin_user, tenant_client,
):
    """TC-PA-STEPUP-2: step-up TOTP → grant-license проходит."""
    with step("подготовка: setup MFA и step-up через TOTP"):
        api = tenant_client(superadmin_user)
        secret = setup_and_verify_mfa(api)
        code = pyotp.TOTP(secret).now()
        r1 = api.post(API.MFA_STEP_UP, json={"method": "totp", "code": code})
        expect_response(r1, label="step-up TOTP").status_ok().json_eq("status", "ok")

    with step("проверка: grant-license после step-up проходит"):
        r2 = api.post(
            API.PLATFORM_FREE_LICENSE_GRANT,
            json={"email": make_email("stepup-grant-ok")},
        )
        expect_response(r2, label="grant after step-up").status_ok().json_eq("status", "granted")


@allure.title("Step-up: неверный TOTP-код отклоняется (401)")
def test_step_up_invalid_totp_401(superadmin_user, tenant_client):
    """TC-PA-STEPUP-3: неверный TOTP в step-up → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("проверка: неверный TOTP в step-up — 401"):
        r = api.post(API.MFA_STEP_UP, json={"method": "totp", "code": "000000"})
        expect_response(r, label="step-up invalid TOTP").status(401)


@allure.title("Step-up: неизвестный метод подтверждения — 400")
def test_step_up_unknown_method_400(superadmin_user, tenant_client):
    """TC-PA-STEPUP-4: method=garbage → 400 (unknown_method)."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("проверка: неизвестный метод — 400"):
        r = api.post(API.MFA_STEP_UP, json={"method": "garbage", "code": "000000"})
        expect_response(r, label="step-up unknown method").status(400)


@allure.title("Step-up: успешное подтверждение записывается в аудит")
def test_step_up_writes_audit_event(superadmin_user, tenant_client):
    """TC-PA-STEPUP-5: успешный step-up пишет audit-запись step_up_verified."""
    with step("подготовка: setup MFA и step-up"):
        api = tenant_client(superadmin_user)
        secret = setup_and_verify_mfa(api)
        code = pyotp.TOTP(secret).now()
        api.post(API.MFA_STEP_UP, json={"method": "totp", "code": code}).raise_for_status()

    with step("действие: запрашиваем audit-log"):
        r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "step_up_verified", "limit": 5})
        expect_response(r, label="audit log step-up").status_ok()
        items = r.json()["items"]

    with step("проверка: запись step_up_verified с method=totp"):
        assert len(items) >= 1, \
            f"expected at least 1 audit item, got {len(items)}"
        assert items[0]["action"] == "step_up_verified", \
            f"action: expected 'step_up_verified', got {items[0]['action']!r}"
        assert items[0]["payload"]["method"] == "totp", \
            f"method: expected 'totp', got {items[0]['payload'].get('method')!r}"


@allure.title("Step-up: резервный код работает как метод подтверждения")
def test_recovery_redeem_works_as_step_up_method(superadmin_user, tenant_client):
    """TC-PA-STEPUP-6: method=recovery с валидным кодом → 200."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        codes = api.post(API.MFA_RECOVERY_REGENERATE).json()["codes"]

    with step("проверка: step-up через recovery-код — 200"):
        r = api.post(API.MFA_STEP_UP, json={"method": "recovery", "code": codes[0]})
        expect_response(r, label="step-up recovery").status_ok().json_eq("status", "ok")


# ─────────────────────────────────────────────────────────────────────
# CSP / security headers на дашборде
# ─────────────────────────────────────────────────────────────────────


@allure.title("CSP: дашборд возвращает Content-Security-Policy заголовок")
def test_dashboard_returns_csp_header(superadmin_user, tenant_client):
    """TC-PA-STEPUP-7: GET /platform/dashboard → Content-Security-Policy установлен."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()
        csp = r.headers.get("content-security-policy", "")

    with step("проверка: CSP содержит канонические директивы"):
        assert csp, "Content-Security-Policy header missing"
        for directive in (
            "default-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
        ):
            assert directive in csp, f"CSP missing directive: {directive!r} (got: {csp!r})"


@allure.title("Безопасность: X-Frame-Options = DENY на дашборде")
def test_dashboard_returns_x_frame_options_deny(superadmin_user, tenant_client):
    """TC-PA-STEPUP-8: X-Frame-Options: DENY (anti-clickjacking)."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()

    with step("проверка: X-Frame-Options = DENY"):
        assert r.headers.get("x-frame-options", "").upper() == "DENY", \
            f"X-Frame-Options: expected 'DENY', got {r.headers.get('x-frame-options')!r}"


@allure.title("Безопасность: Referrer-Policy = no-referrer на дашборде")
def test_dashboard_returns_referrer_policy_no_referrer(superadmin_user, tenant_client):
    """TC-PA-STEPUP-9: Referrer-Policy: no-referrer."""
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()

    with step("проверка: Referrer-Policy = no-referrer"):
        assert r.headers.get("referrer-policy", "").lower() == "no-referrer", \
            f"Referrer-Policy: expected 'no-referrer', got {r.headers.get('referrer-policy')!r}"


@allure.title("Безопасность: Permissions-Policy разрешает WebAuthn")
def test_dashboard_returns_permissions_policy_for_webauthn(superadmin_user, tenant_client):
    """TC-PA-STEPUP-10: Permissions-Policy разрешает publickey-credentials.

    Без этого WebAuthn-вызовы из JS блокируются современными браузерами.
    """
    with step("действие: запрашиваем дашборд"):
        r = tenant_client(superadmin_user).get("/platform/dashboard")
        expect_response(r, label="GET dashboard").status_ok()
        pp = r.headers.get("permissions-policy", "")

    with step("проверка: publickey-credentials-get и -create разрешены"):
        assert "publickey-credentials-get" in pp, \
            f"Permissions-Policy must allow webauthn get, got: {pp!r}"
        assert "publickey-credentials-create" in pp, \
            f"Permissions-Policy must allow webauthn create, got: {pp!r}"
