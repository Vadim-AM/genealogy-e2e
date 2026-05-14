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

import httpx
import pyotp

from tests.api_paths import API
from tests.constants import make_email


def _setup_and_verify_mfa(api: httpx.Client) -> str:
    """Helper: setup + verify TOTP. Returns plaintext secret."""
    setup = api.post(API.MFA_SETUP).json()
    code = pyotp.TOTP(setup["secret"]).now()
    api.post(API.MFA_VERIFY, json={"code": code}).raise_for_status()
    return setup["secret"]


def test_grant_license_403_step_up_required_without_step_up(
    superadmin_user, tenant_client,
):
    """TC-PA-STEPUP-1: critical endpoint требует step_up_verified, иначе 403."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    r = api.post(
        API.PLATFORM_FREE_LICENSE_GRANT,
        json={"email": make_email("stepup-target")},
    )
    assert r.status_code == 403
    assert "step_up_required" in r.text


def test_step_up_with_valid_totp_unlocks_critical_action(
    superadmin_user, tenant_client,
):
    """TC-PA-STEPUP-2: step-up TOTP → grant-license проходит."""
    api = tenant_client(superadmin_user)
    secret = _setup_and_verify_mfa(api)

    # Step-up
    code = pyotp.TOTP(secret).now()
    r1 = api.post(API.MFA_STEP_UP, json={"method": "totp", "code": code})
    r1.raise_for_status()
    assert r1.json()["status"] == "ok"

    # Critical action теперь проходит
    r2 = api.post(
        API.PLATFORM_FREE_LICENSE_GRANT,
        json={"email": make_email("stepup-grant-ok")},
    )
    r2.raise_for_status()
    assert r2.json()["status"] == "granted"


def test_step_up_invalid_totp_401(superadmin_user, tenant_client):
    """TC-PA-STEPUP-3: неверный TOTP в step-up → 401."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    r = api.post(API.MFA_STEP_UP, json={"method": "totp", "code": "000000"})
    assert r.status_code == 401


def test_step_up_unknown_method_400(superadmin_user, tenant_client):
    """TC-PA-STEPUP-4: method=garbage → 400 (unknown_method)."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    r = api.post(API.MFA_STEP_UP, json={"method": "garbage", "code": "000000"})
    assert r.status_code == 400


def test_step_up_writes_audit_event(superadmin_user, tenant_client):
    """TC-PA-STEPUP-5: успешный step-up пишет audit-запись step_up_verified."""
    api = tenant_client(superadmin_user)
    secret = _setup_and_verify_mfa(api)
    code = pyotp.TOTP(secret).now()
    api.post(API.MFA_STEP_UP, json={"method": "totp", "code": code}).raise_for_status()

    r = api.get(API.PLATFORM_AUDIT_LOG, params={"action": "step_up_verified", "limit": 5})
    r.raise_for_status()
    items = r.json()["items"]
    assert len(items) >= 1
    assert items[0]["action"] == "step_up_verified"
    assert items[0]["payload"]["method"] == "totp"


def test_recovery_redeem_works_as_step_up_method(superadmin_user, tenant_client):
    """TC-PA-STEPUP-6: method=recovery с валидным кодом → 200."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    codes = api.post(API.MFA_RECOVERY_REGENERATE).json()["codes"]

    r = api.post(API.MFA_STEP_UP, json={"method": "recovery", "code": codes[0]})
    r.raise_for_status()
    assert r.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────
# CSP / security headers на дашборде
# ─────────────────────────────────────────────────────────────────────


def test_dashboard_returns_csp_header(superadmin_user, tenant_client):
    """TC-PA-STEPUP-7: GET /platform/dashboard → Content-Security-Policy установлен."""
    r = tenant_client(superadmin_user).get("/platform/dashboard")
    r.raise_for_status()
    csp = r.headers.get("content-security-policy", "")
    assert csp, "Content-Security-Policy header missing"
    # Канонические директивы из main.py
    for directive in (
        "default-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
    ):
        assert directive in csp, f"CSP missing directive: {directive!r} (got: {csp!r})"


def test_dashboard_returns_x_frame_options_deny(superadmin_user, tenant_client):
    """TC-PA-STEPUP-8: X-Frame-Options: DENY (anti-clickjacking)."""
    r = tenant_client(superadmin_user).get("/platform/dashboard")
    r.raise_for_status()
    assert r.headers.get("x-frame-options", "").upper() == "DENY"


def test_dashboard_returns_referrer_policy_no_referrer(superadmin_user, tenant_client):
    """TC-PA-STEPUP-9: Referrer-Policy: no-referrer."""
    r = tenant_client(superadmin_user).get("/platform/dashboard")
    r.raise_for_status()
    assert r.headers.get("referrer-policy", "").lower() == "no-referrer"


def test_dashboard_returns_permissions_policy_for_webauthn(superadmin_user, tenant_client):
    """TC-PA-STEPUP-10: Permissions-Policy разрешает publickey-credentials.

    Без этого WebAuthn-вызовы из JS блокируются современными браузерами.
    """
    r = tenant_client(superadmin_user).get("/platform/dashboard")
    r.raise_for_status()
    pp = r.headers.get("permissions-policy", "")
    assert "publickey-credentials-get" in pp, \
        f"Permissions-Policy must allow webauthn get, got: {pp!r}"
    assert "publickey-credentials-create" in pp, \
        f"Permissions-Policy must allow webauthn create, got: {pp!r}"
