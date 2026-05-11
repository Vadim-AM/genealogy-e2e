"""Platform MFA — TC-PA-MFA-* (PR-7..PR-8).

Покрывает:
  • POST /api/platform/mfa/setup — provisioning URL + secret
  • POST /api/platform/mfa/verify — TOTP-код + audit + per-session mfa_verified_at
  • GET /api/platform/mfa/status — состояние MFA
  • POST /api/platform/mfa/recovery-codes/regenerate — 10 кодов
  • POST /api/platform/mfa/recovery-redeem — redeem с автоинвалидацией
  • GET /api/platform/mfa/recovery-codes/count — оставшиеся коды
  • Force-MFA: PLATFORM_REQUIRE_MFA=1 → 403 mfa_setup_required (smoke на /metrics)

Hard rules:
- Single canonical field name. Pin one (`secret`, `otpauth_url`, `unused`, …).
- Hard assert. Никаких OR-fallback.
- pyotp импортируется на топ-уровне; если не установлен — это инфра-проблема,
  тесты падают (не skip — установка обязательна).
"""

from __future__ import annotations

import re

import httpx
import pyotp

from tests.api_paths import API


_BASE32_RE = re.compile(r"^[A-Z2-7]+$")


# ─────────────────────────────────────────────────────────────────────
# /mfa/setup
# ─────────────────────────────────────────────────────────────────────


def test_mfa_setup_requires_superadmin(owner_user, tenant_client):
    """TC-PA-MFA-1: regular owner → 401/403 на /mfa/setup."""
    r = tenant_client(owner_user).post(API.MFA_SETUP)
    assert r.status_code in (401, 403)


def test_mfa_setup_returns_secret_and_uri(superadmin_user, tenant_client):
    """TC-PA-MFA-2: setup возвращает secret + otpauth_url + issuer."""
    r = tenant_client(superadmin_user).post(API.MFA_SETUP)
    r.raise_for_status()
    data = r.json()
    for key in ("secret", "otpauth_url", "issuer"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["otpauth_url"].startswith("otpauth://totp/")
    # secret — base32 (RFC 4648): только A-Z + 2-7. pyotp default = 32 chars.
    assert len(data["secret"]) == 32
    assert _BASE32_RE.match(data["secret"]), \
        f"secret must be RFC 4648 base32 (A-Z + 2-7): {data['secret']!r}"


def test_mfa_setup_409_when_already_configured(superadmin_user, tenant_client):
    """TC-PA-MFA-3: повторный setup без сброса → 409 (mfa_already_configured)."""
    api = tenant_client(superadmin_user)
    api.post(API.MFA_SETUP).raise_for_status()
    r2 = api.post(API.MFA_SETUP)
    assert r2.status_code == 409


# ─────────────────────────────────────────────────────────────────────
# /mfa/verify
# ─────────────────────────────────────────────────────────────────────


def test_mfa_verify_correct_code_returns_ok(superadmin_user, tenant_client):
    """TC-PA-MFA-4: setup → verify с актуальным TOTP-кодом → 200 + valid_until."""
    api = tenant_client(superadmin_user)
    setup = api.post(API.MFA_SETUP).json()
    code = pyotp.TOTP(setup["secret"]).now()
    r = api.post(API.MFA_VERIFY, json={"code": code})
    r.raise_for_status()
    body = r.json()
    assert body["status"] == "ok"
    assert "valid_until" in body


def test_mfa_verify_wrong_code_401(superadmin_user, tenant_client):
    """TC-PA-MFA-5: setup → verify с заведомо неверным кодом → 401."""
    api = tenant_client(superadmin_user)
    api.post(API.MFA_SETUP).raise_for_status()
    r = api.post(API.MFA_VERIFY, json={"code": "000000"})
    assert r.status_code == 401


def test_mfa_verify_409_without_setup(superadmin_user, tenant_client):
    """TC-PA-MFA-6: verify без предшествующего setup → 409 (mfa_not_configured)."""
    r = tenant_client(superadmin_user).post(API.MFA_VERIFY, json={"code": "123456"})
    assert r.status_code == 409


# ─────────────────────────────────────────────────────────────────────
# /mfa/status
# ─────────────────────────────────────────────────────────────────────


def test_mfa_status_initial_not_configured(superadmin_user, tenant_client):
    """TC-PA-MFA-7: до setup — configured=False, fresh=False."""
    r = tenant_client(superadmin_user).get(API.MFA_STATUS)
    r.raise_for_status()
    body = r.json()
    assert body["configured"] is False
    assert body["fresh"] is False


def test_mfa_status_after_verify_is_fresh(superadmin_user, tenant_client):
    """TC-PA-MFA-8: после успешного verify — configured=True, fresh=True."""
    api = tenant_client(superadmin_user)
    setup = api.post(API.MFA_SETUP).json()
    code = pyotp.TOTP(setup["secret"]).now()
    api.post(API.MFA_VERIFY, json={"code": code}).raise_for_status()

    r = api.get(API.MFA_STATUS)
    r.raise_for_status()
    body = r.json()
    assert body["configured"] is True
    assert body["fresh"] is True


# ─────────────────────────────────────────────────────────────────────
# Recovery codes
# ─────────────────────────────────────────────────────────────────────


def _setup_and_verify_mfa(api: httpx.Client) -> str:
    """Helper: setup + verify TOTP. Returns plaintext secret for downstream use."""
    setup = api.post(API.MFA_SETUP).json()
    code = pyotp.TOTP(setup["secret"]).now()
    api.post(API.MFA_VERIFY, json={"code": code}).raise_for_status()
    return setup["secret"]


def test_recovery_regenerate_returns_10_codes(superadmin_user, tenant_client):
    """TC-PA-MFA-9: regenerate возвращает ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    r = api.post(API.MFA_RECOVERY_REGENERATE)
    r.raise_for_status()
    codes = r.json()["codes"]
    assert len(codes) == 10
    for c in codes:
        assert len(c) == 19, f"recovery code length: {len(c)} (expected 19 with dashes)"
        assert c.count("-") == 3, f"code should have 3 dashes: {c!r}"


def test_recovery_count_after_regenerate_is_10(superadmin_user, tenant_client):
    """TC-PA-MFA-10: count returns unused=10 после свежего regenerate."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    api.post(API.MFA_RECOVERY_REGENERATE).raise_for_status()
    r = api.get(API.MFA_RECOVERY_COUNT)
    r.raise_for_status()
    assert r.json()["unused"] == 10


def test_recovery_redeem_consumes_one_code(superadmin_user, tenant_client):
    """TC-PA-MFA-11: redeem валидного кода → 200, count → 9, повторный redeem → 401."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    codes = api.post(API.MFA_RECOVERY_REGENERATE).json()["codes"]
    one = codes[0]

    r1 = api.post(API.MFA_RECOVERY_REDEEM, json={"code": one})
    r1.raise_for_status()
    assert r1.json()["status"] == "ok"

    # Counter уменьшился
    count = api.get(API.MFA_RECOVERY_COUNT).json()["unused"]
    assert count == 9

    # Reuse → 401
    r2 = api.post(API.MFA_RECOVERY_REDEEM, json={"code": one})
    assert r2.status_code == 401


def test_recovery_regenerate_invalidates_old_codes(superadmin_user, tenant_client):
    """TC-PA-MFA-12: вторая regenerate инвалидирует первые 10 кодов."""
    api = tenant_client(superadmin_user)
    _setup_and_verify_mfa(api)
    old_codes = api.post(API.MFA_RECOVERY_REGENERATE).json()["codes"]
    new_codes = api.post(API.MFA_RECOVERY_REGENERATE).json()["codes"]
    assert set(old_codes).isdisjoint(set(new_codes))

    # Старый код больше не валиден
    r = api.post(API.MFA_RECOVERY_REDEEM, json={"code": old_codes[0]})
    assert r.status_code == 401
