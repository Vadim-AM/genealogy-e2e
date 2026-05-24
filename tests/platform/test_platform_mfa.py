"""Platform MFA — TC-PA-MFA-* (PR-7..PR-8)."""

from __future__ import annotations

import re
from http import HTTPStatus

import allure
import pyotp

from api import mfa_api, routes
from assertions.base import should
from fixtures.users import setup_and_verify_mfa
from framework.response import expect_response
from framework.step import step
from models.mfa import MfaVerifyResponse
from src.texts import ErrMsg

_BASE32_RE = re.compile(r"^[A-Z2-7]+$")


@allure.title("MFA: настройка запрещена обычному владельцу")
def test_mfa_setup_requires_superadmin(owner_user, tenant_client) -> None:
    """TC-PA-MFA-1: regular owner → 401/403 на /mfa/setup."""
    r = tenant_client(owner_user).post(routes.MFA_SETUP)
    expect_response(r, label="owner MFA setup").status(HTTPStatus.FORBIDDEN)


@allure.title("MFA: setup возвращает secret, otpauth-ссылку и issuer")
def test_mfa_setup_returns_secret_and_uri(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-2: setup возвращает secret + otpauth_url + issuer."""
    with step("действие: вызываем MFA setup"):
        setup = mfa_api.setup_mfa(tenant_client(superadmin_user))

    with step("проверка: secret, otpauth_url, issuer корректны"):
        should.be_true(setup.otpauth_url.startswith("otpauth://totp/"), ErrMsg.mfa_otpauth_wrong)
        # secret — base32 (RFC 4648): только A-Z + 2-7. pyotp default = 32 chars.
        should.have_length(setup.secret, 32, ErrMsg.mfa_secret_wrong)
        should.be_true(_BASE32_RE.match(setup.secret), ErrMsg.mfa_secret_wrong)


@allure.title("MFA: повторный setup без сброса отклоняется (409)")
def test_mfa_setup_409_when_already_configured(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-3: повторный setup без сброса → 409 (mfa_already_configured)."""
    api = tenant_client(superadmin_user)

    with step("подготовка: первый setup"):
        mfa_api.setup_mfa(api)

    with step("проверка: повторный setup отклоняется 409"):
        r2 = api.post(routes.MFA_SETUP)
        expect_response(r2, label="MFA setup duplicate").status(HTTPStatus.CONFLICT)


@allure.title("MFA: верный TOTP-код подтверждает двухфакторку")
def test_mfa_verify_correct_code_returns_ok(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-4: setup → verify с актуальным TOTP-кодом → 200 + valid_until."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA и генерация TOTP-кода"):
        setup = mfa_api.setup_mfa(api)
        code = pyotp.TOTP(setup.secret).now()

    with step("действие: verify с актуальным кодом"):
        verified = mfa_api.verify_mfa(api, code)

    with step("проверка: status=ok и valid_until присутствует"):
        should.be_equal(verified.status, "ok", ErrMsg.mfa_verify_status_wrong)
        should.not_none(verified.valid_until, ErrMsg.mfa_valid_until_missing)


@allure.title("MFA: неверный TOTP-код отклоняется (401)")
def test_mfa_verify_wrong_code_401(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-5: setup → verify с заведомо неверным кодом → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA"):
        mfa_api.setup_mfa(api)

    with step("проверка: неверный код отклоняется 401"):
        r = api.post(routes.MFA_VERIFY, json={"code": "000000"})
        expect_response(r, label="MFA verify wrong code").status(HTTPStatus.UNAUTHORIZED)


@allure.title("MFA: verify без предварительного setup отклоняется (409)")
def test_mfa_verify_409_without_setup(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-6: verify без предшествующего setup → 409 (mfa_not_configured)."""
    r = tenant_client(superadmin_user).post(routes.MFA_VERIFY, json={"code": "123456"})
    expect_response(r, label="MFA verify without setup").status(HTTPStatus.CONFLICT)


@allure.title("MFA: статус до настройки — не сконфигурировано")
def test_mfa_status_initial_not_configured(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-7: до setup — configured=False, fresh=False."""
    status = mfa_api.get_mfa_status(tenant_client(superadmin_user))
    should.be_false(status.configured, ErrMsg.mfa_configured_wrong)
    should.be_false(status.fresh, ErrMsg.mfa_fresh_wrong)


@allure.title("MFA: после подтверждения статус — сконфигурировано и свежее")
def test_mfa_status_after_verify_is_fresh(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-8: после успешного verify — configured=True, fresh=True."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup = mfa_api.setup_mfa(api)
        code = pyotp.TOTP(setup.secret).now()
        mfa_api.verify_mfa(api, code)

    with step("проверка: статус configured=True, fresh=True"):
        status = mfa_api.get_mfa_status(api)
        should.be_true(status.configured, ErrMsg.mfa_configured_wrong)
        should.be_true(status.fresh, ErrMsg.mfa_fresh_wrong)


@allure.title("MFA: генерация выдаёт ровно 10 резервных кодов")
def test_recovery_regenerate_returns_10_codes(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-9: regenerate возвращает ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup + verify MFA"):
        setup_and_verify_mfa(api)

    with step("действие: генерируем резервные коды"):
        recovery = mfa_api.regenerate_recovery_codes(api)
        codes = recovery.codes

    with step("проверка: ровно 10 кодов в формате xxxx-xxxx-xxxx-xxxx"):
        should.have_length(codes, 10, ErrMsg.recovery_code_count_wrong)
        for c in codes:
            should.have_length(c, 19, ErrMsg.recovery_code_format_wrong)
            should.be_equal(c.count("-"), 3, ErrMsg.recovery_code_format_wrong)


@allure.title("MFA: счётчик резервных кодов равен 10 после генерации")
def test_recovery_count_after_regenerate_is_10(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-10: count returns unused=10 после свежего regenerate."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        mfa_api.regenerate_recovery_codes(api)

    with step("проверка: unused=10"):
        count = mfa_api.get_recovery_count(api)
        should.be_equal(count.unused, 10, ErrMsg.recovery_unused_wrong)


@allure.title("MFA: использование резервного кода уменьшает счётчик")
def test_recovery_redeem_consumes_one_code(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-11: redeem валидного кода → 200, count → 9, повторный redeem → 401."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + regenerate кодов"):
        setup_and_verify_mfa(api)
        recovery = mfa_api.regenerate_recovery_codes(api)
        one = recovery.codes[0]

    with step("действие: redeem первого кода"):
        r1 = api.post(routes.MFA_RECOVERY_REDEEM, json={"code": one})
        resp = expect_response(r1, label="recovery redeem").status_ok().schema(MfaVerifyResponse)
        should.be_equal(resp.status, "ok", ErrMsg.recovery_redeem_status_wrong)

    with step("проверка: счётчик уменьшился до 9"):
        count = mfa_api.get_recovery_count(api)
        should.be_equal(count.unused, 9, ErrMsg.recovery_unused_wrong)

    with step("проверка: повторный redeem того же кода — 401"):
        r2 = api.post(routes.MFA_RECOVERY_REDEEM, json={"code": one})
        expect_response(r2, label="recovery redeem reuse").status(HTTPStatus.UNAUTHORIZED)


@allure.title("MFA: перегенерация инвалидирует старые резервные коды")
def test_recovery_regenerate_invalidates_old_codes(superadmin_user, tenant_client) -> None:
    """TC-PA-MFA-12: вторая regenerate инвалидирует первые 10 кодов."""
    api = tenant_client(superadmin_user)

    with step("подготовка: setup MFA + два regenerate"):
        setup_and_verify_mfa(api)
        old_codes = mfa_api.regenerate_recovery_codes(api).codes
        new_codes = mfa_api.regenerate_recovery_codes(api).codes

    with step("проверка: старые и новые коды не пересекаются"):
        should.be_true(set(old_codes).isdisjoint(set(new_codes)), ErrMsg.recovery_not_invalidated)

    with step("проверка: старый код больше не валиден — 401"):
        r = api.post(routes.MFA_RECOVERY_REDEEM, json={"code": old_codes[0]})
        expect_response(r, label="old recovery code").status(HTTPStatus.UNAUTHORIZED)
