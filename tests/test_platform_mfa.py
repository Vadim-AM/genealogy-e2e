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

import httpx
import pyotp

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────
# /mfa/setup
# ─────────────────────────────────────────────────────────────────────


def test_mfa_setup_requires_superadmin(owner_user, base_url: str):
    """TC-PA-MFA-1: regular owner → 401/403 на /mfa/setup."""
    r = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=owner_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code in (401, 403)


def test_mfa_setup_returns_secret_and_uri(superadmin_user, base_url: str):
    """TC-PA-MFA-2: setup возвращает secret + otpauth_url + issuer."""
    r = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    for key in ("secret", "otpauth_url", "issuer"):
        assert key in data, f"field {key!r} missing: {sorted(data)}"
    assert data["otpauth_url"].startswith("otpauth://totp/")
    # secret — base32, длина 32 символа (pyotp default)
    assert len(data["secret"]) == 32
    assert data["secret"].isupper() or data["secret"].isalnum()


def test_mfa_setup_409_when_already_configured(superadmin_user, base_url: str):
    """TC-PA-MFA-3: повторный setup без сброса → 409 (mfa_already_configured)."""
    r1 = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r1.raise_for_status()
    r2 = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r2.status_code == 409


# ─────────────────────────────────────────────────────────────────────
# /mfa/verify
# ─────────────────────────────────────────────────────────────────────


def test_mfa_verify_correct_code_returns_ok(superadmin_user, base_url: str):
    """TC-PA-MFA-4: setup → verify с актуальным TOTP-кодом → 200 + valid_until."""
    setup = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()
    code = pyotp.TOTP(setup["secret"]).now()
    r = httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": code},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    body = r.json()
    assert body["status"] == "ok"
    assert "valid_until" in body


def test_mfa_verify_wrong_code_401(superadmin_user, base_url: str):
    """TC-PA-MFA-5: setup → verify с заведомо неверным кодом → 401."""
    httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    r = httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": "000000"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 401


def test_mfa_verify_409_without_setup(superadmin_user, base_url: str):
    """TC-PA-MFA-6: verify без предшествующего setup → 409 (mfa_not_configured)."""
    r = httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": "123456"},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 409


# ─────────────────────────────────────────────────────────────────────
# /mfa/status
# ─────────────────────────────────────────────────────────────────────


def test_mfa_status_initial_not_configured(superadmin_user, base_url: str):
    """TC-PA-MFA-7: до setup — configured=False, fresh=False."""
    r = httpx.get(
        f"{base_url}{API.MFA_STATUS}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    body = r.json()
    assert body["configured"] is False
    assert body["fresh"] is False


def test_mfa_status_after_verify_is_fresh(superadmin_user, base_url: str):
    """TC-PA-MFA-8: после успешного verify — configured=True, fresh=True."""
    setup = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()
    code = pyotp.TOTP(setup["secret"]).now()
    httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": code},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    r = httpx.get(
        f"{base_url}{API.MFA_STATUS}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    body = r.json()
    assert body["configured"] is True
    assert body["fresh"] is True


# ─────────────────────────────────────────────────────────────────────
# Recovery codes
# ─────────────────────────────────────────────────────────────────────


def _setup_and_verify_mfa(client_cookies: dict, base_url: str) -> str:
    """Helper: setup + verify TOTP. Возвращает plaintext-secret для последующих
    кодов (если потребуются в тесте)."""
    setup = httpx.post(
        f"{base_url}{API.MFA_SETUP}",
        cookies=client_cookies,
        timeout=TIMEOUTS.api_request,
    ).json()
    code = pyotp.TOTP(setup["secret"]).now()
    httpx.post(
        f"{base_url}{API.MFA_VERIFY}",
        json={"code": code},
        cookies=client_cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    return setup["secret"]


def test_recovery_regenerate_returns_10_codes(superadmin_user, base_url: str):
    """TC-PA-MFA-9: regenerate возвращает ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    r = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    codes = r.json()["codes"]
    assert len(codes) == 10
    for c in codes:
        assert len(c) == 19, f"recovery code length: {len(c)} (expected 19 with dashes)"
        assert c.count("-") == 3, f"code should have 3 dashes: {c!r}"


def test_recovery_count_after_regenerate_is_10(superadmin_user, base_url: str):
    """TC-PA-MFA-10: count returns unused=10 после свежего regenerate."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    r = httpx.get(
        f"{base_url}{API.MFA_RECOVERY_COUNT}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    assert r.json()["unused"] == 10


def test_recovery_redeem_consumes_one_code(superadmin_user, base_url: str):
    """TC-PA-MFA-11: redeem валидного кода → 200, count → 9, повторный redeem → 401."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    codes = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()["codes"]
    one = codes[0]

    r1 = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REDEEM}",
        json={"code": one},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    r1.raise_for_status()
    assert r1.json()["status"] == "ok"

    # Counter уменьшился
    count = httpx.get(
        f"{base_url}{API.MFA_RECOVERY_COUNT}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()["unused"]
    assert count == 9

    # Reuse → 401
    r2 = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REDEEM}",
        json={"code": one},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r2.status_code == 401


def test_recovery_regenerate_invalidates_old_codes(superadmin_user, base_url: str):
    """TC-PA-MFA-12: вторая regenerate инвалидирует первые 10 кодов."""
    _setup_and_verify_mfa(superadmin_user.cookies, base_url)
    old_codes = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()["codes"]

    new_codes = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REGENERATE}",
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    ).json()["codes"]
    assert set(old_codes).isdisjoint(set(new_codes))

    # Старый код больше не валиден
    r = httpx.post(
        f"{base_url}{API.MFA_RECOVERY_REDEEM}",
        json={"code": old_codes[0]},
        cookies=superadmin_user.cookies,
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 401
