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

import allure
import pyotp

from tests._core.api_paths import API
from tests._core.response import expect_response
from tests._core.step import step
from tests._fixtures.users import setup_and_verify_mfa
from tests.helpers.api import mfa_api

_BASE32_RE = re.compile(r"^[A-Z2-7]+$")


# ─────────────────────────────────────────────────────────────────────
# /mfa/setup
# ─────────────────────────────────────────────────────────────────────


@allure.title("MFA: настройка запрещена обычному владельцу")
def test_mfa_setup_requires_superadmin(owner_user, tenant_client):
    """TC-PA-MFA-1: regular owner → 401/403 на /mfa/setup."""
    r = tenant_client(owner_user).post(API.MFA_SETUP)
    expect_response(r, label="owner MFA setup").status(403)


@allure.title("MFA: setup возвращает secret, otpauth-ссылку и issuer")
def test_mfa_setup_returns_secret_and_uri(superadmin_user, tenant_client):
    """TC-PA-MFA-2: setup возвращает secret + otpauth_url + issuer."""
    with step("действие: вызываем MFA setup"):
        setup = mfa_api.setup_mfa(tenant_client(superadmin_user))

    with step("проверка: secret, otpauth_url, issuer корректны"):
        assert setup.otpauth_url.startswith("otpauth://totp/"), \
            f"otpauth_url must start with 'otpauth://totp/', got {setup.otpauth_url[:40]!r}"
        # secret — base32 (RFC 4648): только A-Z + 2-7. pyotp default = 32 chars.
        assert len(setup.secret) == 32, \
            f"secret length: expected 32, got {len(setup.secret)}"
        assert _BASE32_RE.match(setup.secret), \
            f"secret must be RFC 4648 base32 (A-Z + 2-7): {setup.secret!r}"


@allure.title("MFA: повторный setup без сброса отклоняется (409)")
def test_mfa_setup_409_when_already_configured(superadmin_user, tenant_client):
    """TC-PA-MFA-3: повторный setup без сброса → 409 (mfa_already_configured)."""
    api = tenant_client(superadmin_user)

    with step("подготовка: первый setup"):
        mfa_api.setup_mfa(api)

    with step("проверка: повторный setup отклоняется 409"):
        r2 = api.post(API.MFA_SETUP)
        expect_response(r2, label="MFA setup duplicate").status(409)


# ─────────────────────────────────────────────────────────────────────
# /mfa/verify
# ─────────────────────────────────────────────────────────────────────


@allure.title("MFA: верный TOTP-код подтверждает двухфакторку")
def test_mfa_verify_correct_code_returns_ok(superadmin_user, tenant_client):
    """TC-PA-MFA-4: setup → verify с актуальным TOTP-кодом → 200 + valid_until."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA и генерация TOTP-кода"):
        setup = mfa_api.setup_mfa(api)
        code = pyotp.TOTP(setup.secret).now()

    with step("действие: verify с актуальным кодом"):
        verified = mfa_api.verify_mfa(api, code)

    with step("проверка: status=ok и valid_until присутствует"):
        assert verified.status == "ok", \
            f"status: expected 'ok', got {verified.status!r}"
        assert verified.valid_until is not None, \
            "valid_until missing from response"


@allure.title("MFA: неверный TOTP-код отклоняется (401)")
def test_mfa_verify_wrong_code_401(superadmin_user, tenant_client):
    """TC-PA-MFA-5: setup → verify с заведомо неверным кодом → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA"):
        mfa_api.setup_mfa(api)

    with step("проверка: неверный код отклоняется 401"):
        r = api.post(API.MFA_VERIFY, json={"code": "000000"})
        expect_response(r, label="MFA verify wrong code").status(401)


@allure.title("MFA: verify без предварительного setup отклоняется (409)")
def test_mfa_verify_409_without_setup(superadmin_user, tenant_client):
    """TC-PA-MFA-6: verify без предшествующего setup → 409 (mfa_not_configured)."""
    r = tenant_client(superadmin_user).post(API.MFA_VERIFY, json={"code": "123456"})
    expect_response(r, label="MFA verify without setup").status(409)


# ─────────────────────────────────────────────────────────────────────
# /mfa/status
# ─────────────────────────────────────────────────────────────────────


@allure.title("MFA: статус до настройки — не сконфигурировано")
def test_mfa_status_initial_not_configured(superadmin_user, tenant_client):
    """TC-PA-MFA-7: до setup — configured=False, fresh=False."""
    status = mfa_api.get_mfa_status(tenant_client(superadmin_user))
    assert status.configured is False, f"configured: expected False, got {status.configured!r}"
    assert status.fresh is False, f"fresh: expected False, got {status.fresh!r}"


@allure.title("MFA: после подтверждения статус — сконфигурировано и свежее")
def test_mfa_status_after_verify_is_fresh(superadmin_user, tenant_client):
    """TC-PA-MFA-8: после успешного verify — configured=True, fresh=True."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup = mfa_api.setup_mfa(api)
        code = pyotp.TOTP(setup.secret).now()
        mfa_api.verify_mfa(api, code)

    with step("проверка: статус configured=True, fresh=True"):
        status = mfa_api.get_mfa_status(api)
        assert status.configured is True, f"configured: expected True, got {status.configured!r}"
        assert status.fresh is True, f"fresh: expected True, got {status.fresh!r}"


# ─────────────────────────────────────────────────────────────────────
# Recovery codes
# ─────────────────────────────────────────────────────────────────────


@allure.title("MFA: генерация выдаёт ровно 10 резервных кодов")
def test_recovery_regenerate_returns_10_codes(superadmin_user, tenant_client):
    """TC-PA-MFA-9: regenerate возвращает ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("действие: генерируем резервные коды"):
        recovery = mfa_api.regenerate_recovery_codes(api)
        codes = recovery.codes

    with step("проверка: ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx"):
        assert len(codes) == 10, \
            f"regenerate must return 10 codes, got {len(codes)}"
        for c in codes:
            assert len(c) == 19, f"recovery code length: {len(c)} (expected 19 with dashes)"
            assert c.count("-") == 3, f"code should have 3 dashes: {c!r}"


@allure.title("MFA: счётчик резервных кодов равен 10 после генерации")
def test_recovery_count_after_regenerate_is_10(superadmin_user, tenant_client):
    """TC-PA-MFA-10: count returns unused=10 после свежего regenerate."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        mfa_api.regenerate_recovery_codes(api)

    with step("проверка: unused=10"):
        count = mfa_api.get_recovery_count(api)
        assert count.unused == 10, f"expected unused=10, got {count.unused}"


@allure.title("MFA: использование резервного кода уменьшает счётчик")
def test_recovery_redeem_consumes_one_code(superadmin_user, tenant_client):
    """TC-PA-MFA-11: redeem валидного кода → 200, count → 9, повторный redeem → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        recovery = mfa_api.regenerate_recovery_codes(api)
        one = recovery.codes[0]

    with step("действие: redeem первого кода"):
        r1 = api.post(API.MFA_RECOVERY_REDEEM, json={"code": one})
        expect_response(r1, label="recovery redeem").status_ok().json_eq("status", "ok")

    with step("проверка: счётчик уменьшился до 9"):
        count = mfa_api.get_recovery_count(api)
        assert count.unused == 9, \
            f"one code redeemed, expected 9 remaining, got {count.unused}"

    with step("проверка: повторный redeem того же кода — 401"):
        r2 = api.post(API.MFA_RECOVERY_REDEEM, json={"code": one})
        expect_response(r2, label="recovery redeem reuse").status(401)


@allure.title("MFA: перегенерация инвалидирует старые резервные коды")
def test_recovery_regenerate_invalidates_old_codes(superadmin_user, tenant_client):
    """TC-PA-MFA-12: вторая regenerate инвалидирует первые 10 кодов."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + два regenerate"):
        setup_and_verify_mfa(api)
        old_codes = mfa_api.regenerate_recovery_codes(api).codes
        new_codes = mfa_api.regenerate_recovery_codes(api).codes

    with step("проверка: старые и новые коды не пересекаются"):
        assert set(old_codes).isdisjoint(set(new_codes)), \
            "second regenerate must invalidate all old codes"

    with step("проверка: старый код больше не валиден — 401"):
        r = api.post(API.MFA_RECOVERY_REDEEM, json={"code": old_codes[0]})
        expect_response(r, label="old recovery code").status(401)
