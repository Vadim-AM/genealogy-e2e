"""POM for the user's 2FA settings — owner.html "Безопасность" tab.

Selectors from owner.html + js/owner-mfa.js. The tab lazy-loads owner-mfa.js
on first open. 2FA is opt-in; the product has no login-time TOTP prompt —
2FA gates critical ops via a 5-minute step-up window instead.

Layout:
    [data-tab="security"]      ← opens the Security tab
      #mfaStatusText           ← "✅ 2FA включена" / "❌ 2FA отключена"
      #mfaEnableBtn #mfaDisableBtn #mfaRegenerateBtn
      #mfaSetupSecret          ← TOTP secret (setup dialog)
      #mfaVerifyCode           ← 6-digit code input
      #mfaRecoveryList > li    ← 10 recovery codes
      #mfaRecoveryDoneBtn
      #mfaStepUpCode           ← step-up code input (disable)
"""

from __future__ import annotations

from typing import Self

import pyotp
from playwright.sync_api import Page, expect


class MfaSettings:
    """Drives the owner's 2FA settings: enable, verify, recovery, disable."""

    def __init__(self, page: Page):
        self.page = page
        self.tab = page.locator('[data-tab="security"]')
        self.status_text = page.locator("#mfaStatusText")
        self.btn_enable = page.locator("#mfaEnableBtn")
        self.btn_disable = page.locator("#mfaDisableBtn")
        self.setup_secret = page.locator("#mfaSetupSecret")
        self.verify_code = page.locator("#mfaVerifyCode")
        self.recovery_codes = page.locator("#mfaRecoveryList li")
        self.recovery_done = page.locator("#mfaRecoveryDoneBtn")
        self.stepup_code = page.locator("#mfaStepUpCode")
        self._secret: str | None = None

    def open_tab(self) -> Self:
        """Click the Security tab to reveal MFA controls."""
        self.tab.click()
        return self

    def enable_with_totp(self) -> None:
        """Click Enable → read the TOTP secret → submit a generated code."""
        self.btn_enable.click()
        expect(self.setup_secret).to_be_visible()
        self._secret = self.setup_secret.inner_text().strip()
        self.verify_code.fill(pyotp.TOTP(self._secret).now())
        self.verify_code.press("Enter")

    def finish_recovery(self) -> None:
        """The verify step shows 10 recovery codes — acknowledge them."""
        expect(self.recovery_codes).to_have_count(10)
        self.recovery_done.click()

    def disable_with_stepup(self) -> None:
        """Click Disable → step-up dialog → submit a generated TOTP code."""
        self.btn_disable.click()
        expect(self.stepup_code).to_be_visible()
        assert self._secret, "enable_with_totp must run before disable"
        self.stepup_code.fill(pyotp.TOTP(self._secret).now())
        self.stepup_code.press("Enter")
