"""User 2FA journey — owner enables account 2FA, then disables it.

The product has no login-time TOTP prompt (2FA gates critical ops via a
step-up window, not login), so the journey is: open Security settings →
enable with a TOTP code → acknowledge recovery codes → status shows "on"
→ disable via a step-up code → status shows "off".

A second backend-invariant test covers the recovery-code lifecycle
(regenerate / count / redeem) — one-time semantics, no dedicated UI.
"""

from __future__ import annotations

import pyotp
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.constants import make_email
from tests.messages import Mfa, t
from tests.pages.mfa_settings import MfaSettings


def test_owner_enables_then_disables_2fa(owner_page: Page, owner_user):
    """Owner opens Security settings → enables 2FA with a TOTP code →
    acknowledges recovery codes → status shows on; disables via step-up
    → status shows off."""
    owner_page.goto("/owner")
    owner_page.wait_for_load_state("domcontentloaded")

    mfa = MfaSettings(owner_page).open_tab()
    expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_OFF))

    mfa.enable_with_totp()
    mfa.finish_recovery()
    expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_ON))

    mfa.disable_with_stepup()
    expect(mfa.status_text).to_contain_text(t(Mfa.STATUS_OFF))


def test_user_mfa_recovery_codes_are_one_time(signup_via_api, tenant_client):
    """Backend invariant: recovery codes are one-time. Enable 2FA,
    regenerate to obtain the codes, redeem one → the unused count drops,
    re-redeeming the same code → 401."""
    user = signup_via_api(email=make_email("mfa-recovery"))
    api = tenant_client(user)

    setup = api.post(API.USER_MFA_SETUP)
    setup.raise_for_status()
    secret = setup.json()["secret"]
    api.post(
        API.USER_MFA_VERIFY, json={"code": pyotp.TOTP(secret).now()},
    ).raise_for_status()

    regen = api.post(API.USER_MFA_RECOVERY_REGEN)
    regen.raise_for_status()
    codes = regen.json()["codes"]
    assert len(codes) == 10, f"expected 10 recovery codes, got {len(codes)}"

    count_before = api.get(API.USER_MFA_RECOVERY_COUNT).json()["unused"]
    assert count_before == 10

    api.post(
        API.USER_MFA_RECOVERY_REDEEM, json={"code": codes[0]},
    ).raise_for_status()
    count_after = api.get(API.USER_MFA_RECOVERY_COUNT).json()["unused"]
    assert count_after == 9, \
        f"redeeming a code must decrement the count: {count_before}→{count_after}"

    again = api.post(API.USER_MFA_RECOVERY_REDEEM, json={"code": codes[0]})
    assert again.status_code == 401, \
        f"a recovery code must be one-time; re-redeem got {again.status_code}"
