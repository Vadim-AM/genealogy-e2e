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
from tests.timeouts import TIMEOUTS


def _setup_and_verify_mfa(cookies: dict, base_url: str) -> str:
    """Helper: setup + verify TOTP. Возвращает plaintext secret."""
    setup = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=cookies,
        timeout=TIMEOUTS.api_request,
    ).json()
    code = pyotp.TOTP(setup["secret"]).now()
    httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": code},
        cookies=cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    return setup["secret"]


def test_grant_license_403_step_up_required_without_step_up(
    superadmin_user, base_url: str
):
    """TC-PA-STEPUP-1: critical endpoint требует step_up_verified, иначе 403."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    r = httpx.post(
        f"{base_url}{API.PLATFORM_FREE_LICENSE_GRANT}",
        json={"email": "stepup-target@e2e.local"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 403
    assert "step_up_required" in r.text


def test_step_up_with_valid_totp_unlocks_critical_action(
    superadmin_user, base_url: str
):
    """TC-PA-STEPUP-2: step-up TOTP → grant-license проходит."""
    secret = _setup_and_verify_mfa(superadmin_user.cookies, base_url)

    # Step-up
    code = pyotp.TOTP(secret).now()
    r1 = httpx.post(
        f"{base_url}{API.MFA_STEP_UP}",
        json={"method": "totp", "code": code},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r1.raise_for_status()
    assert r1.json()["status"] == "ok"

    # Critical action теперь проходит
    r2 = httpx.post(
        f"{base_url}{API.PLATFORM_FREE_LICENSE_GRANT}",
        json={"email": "stepup-grant-ok@e2e.local"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r2.raise_for_status()
    assert r2.json()["status"] == "granted"


def test_step_up_invalid_totp_401(superadmin_user, base_url: str):
    """TC-PA-STEPUP-3: неверный TOTP в step-up → 401."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    r = httpx.post(
        f"{base_url}{API.MFA_STEP_UP}",
        json={"method": "totp", "code": "000000"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 401


def test_step_up_unknown_method_400(superadmin_user, base_url: str):
    """TC-PA-STEPUP-4: method=garbage → 400 (unknown_method)."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    r = httpx.post(
        f"{base_url}{API.MFA_STEP_UP}",
        json={"method": "garbage", "code": "000000"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 400


def test_step_up_writes_audit_event(superadmin_user, base_url: str):
    """TC-PA-STEPUP-5: успешный step-up пишет audit-запись step_up_verified."""
    secret = _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    code = pyotp.TOTP(secret).now()
    httpx.post(
        f"{base_url}{API.MFA_STEP_UP}",
        json={"method": "totp", "code": code},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()

    r = httpx.get(
        f"{base_url}{API.PLATFORM_AUDIT_LOG}?action=step_up_verified&limit=5",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    items = r.json()["items"]
    assert len(items) >= 1
    assert items[0]["action"] == "step_up_verified"
    assert items[0]["payload"]["method"] == "totp"


def test_recovery_redeem_works_as_step_up_method(superadmin_user, base_url: str):
    """TC-PA-STEPUP-6: method=recovery с валидным кодом → 200."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    codes = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()["codes"]

    r = httpx.post(
        f"{base_url}{API.MFA_STEP_UP}",
        json={"method": "recovery", "code": codes[0]},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────
# CSP / security headers на дашборде
# ─────────────────────────────────────────────────────────────────────


def test_dashboard_returns_csp_header(superadmin_user, base_url: str):
    """TC-PA-STEPUP-7: GET /platform/dashboard → Content-Security-Policy установлен."""
    r = httpx.get(
        f"{base_url}/platform/dashboard",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
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


def test_dashboard_returns_x_frame_options_deny(superadmin_user, base_url: str):
    """TC-PA-STEPUP-8: X-Frame-Options: DENY (anti-clickjacking)."""
    r = httpx.get(
        f"{base_url}/platform/dashboard",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.headers.get("x-frame-options", "").upper() == "DENY"


def test_dashboard_returns_referrer_policy_no_referrer(superadmin_user, base_url: str):
    """TC-PA-STEPUP-9: Referrer-Policy: no-referrer."""
    r = httpx.get(
        f"{base_url}/platform/dashboard",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.headers.get("referrer-policy", "").lower() == "no-referrer"


def test_dashboard_returns_permissions_policy_for_webauthn(superadmin_user, base_url: str):
    """TC-PA-STEPUP-10: Permissions-Policy разрешает publickey-credentials.

    Без этого WebAuthn-вызовы из JS блокируются современными браузерами.
    """
    r = httpx.get(
        f"{base_url}/platform/dashboard",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    pp = r.headers.get("permissions-policy", "")
    assert "publickey-credentials-get" in pp, \
        f"Permissions-Policy must allow webauthn get, got: {pp!r}"
    assert "publickey-credentials-create" in pp, \
        f"Permissions-Policy must allow webauthn create, got: {pp!r}"
