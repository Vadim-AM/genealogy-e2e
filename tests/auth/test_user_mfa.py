"""User 2FA journey — owner enables account 2FA, then disables it.

The product has no login-time TOTP prompt (2FA gates critical ops via a
step-up window, not login), so the journey is: open Security settings →
enable with a TOTP code → acknowledge recovery codes → status shows "on"
→ disable via a step-up code → status shows "off".

A second backend-invariant test covers the recovery-code lifecycle
(regenerate / count / redeem) — one-time semantics, no dedicated UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import pyotp
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.constants import make_email
from tests._core.messages import Mfa, t
from tests._core.response import expect_response
from tests._core.step import step
from tests.pages.mfa_settings import MfaSettings
from tests.pages.owner_page import OwnerPage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@allure.title("Владелец включает и затем отключает двухфакторную аутентификацию")
def test_owner_enables_then_disables_2fa(owner_page: Page, owner_user, pages: PageFactory):
    """Owner opens Security settings → enables 2FA with a TOTP code →
    acknowledges recovery codes → status shows on; disables via step-up
    → status shows off."""
    with step("подготовка: открытие вкладки безопасности, статус выключен"):
        pages.navigate_to(OwnerPage)
        mfa = MfaSettings(owner_page).open_tab()
        expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_OFF))

    with step("действие: включение 2FA через TOTP"):
        mfa.enable_with_totp()
        mfa.finish_recovery()
        expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_ON))

    with step("действие: отключение 2FA через step-up"):
        mfa.disable_with_stepup()
        expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_OFF))


@allure.title("Код восстановления 2FA можно использовать только один раз")
def test_user_mfa_recovery_codes_are_one_time(signup_via_api, tenant_client):
    """Backend invariant: recovery codes are one-time. Enable 2FA,
    regenerate to obtain the codes, redeem one → the unused count drops,
    re-redeeming the same code → 401."""
    with step("подготовка: signup и включение 2FA"):
        user = signup_via_api(email=make_email("mfa-recovery"))
        api = tenant_client(user)

        setup_data = expect_response(
            api.post(API.USER_MFA_SETUP), label="user MFA setup",
        ).status_ok().data
        secret = setup_data["secret"]
        expect_response(
            api.post(API.USER_MFA_VERIFY, json={"code": pyotp.TOTP(secret).now()}),
            label="user MFA verify",
        ).status_ok()

    with step("действие: регенерация кодов и проверка количества"):
        regen_data = expect_response(
            api.post(API.USER_MFA_RECOVERY_REGEN), label="user MFA regen",
        ).status_ok().data
        codes = regen_data["codes"]
        assert len(codes) == 10, f"expected 10 recovery codes, got {len(codes)}"

        count_data = expect_response(
            api.get(API.USER_MFA_RECOVERY_COUNT), label="user MFA recovery count",
        ).status_ok().data
        count_before = count_data["unused"]
        assert count_before == 10, \
            f"fresh regenerate should yield 10 codes, got {count_before}"

    with step("действие: использование кода и проверка декремента"):
        expect_response(
            api.post(API.USER_MFA_RECOVERY_REDEEM, json={"code": codes[0]}),
            label="user MFA redeem",
        ).status_ok()
        count_after_data = expect_response(
            api.get(API.USER_MFA_RECOVERY_COUNT), label="user MFA recovery count after",
        ).status_ok().data
        count_after = count_after_data["unused"]
        assert count_after == 9, \
            f"redeeming a code must decrement the count: {count_before}→{count_after}"

    with step("проверка: повторное использование того же кода — 401"):
        again = api.post(API.USER_MFA_RECOVERY_REDEEM, json={"code": codes[0]})
        assert again.status_code == 401, \
            f"a recovery code must be one-time; re-redeem got {again.status_code}"
