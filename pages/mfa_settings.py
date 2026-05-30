"""POM for the user's 2FA settings — owner.html "Безопасность" tab.

Selectors from owner.html + js/owner-mfa.js. The tab lazy-loads owner-mfa.js
on first open. 2FA is opt-in; the product has no login-time TOTP prompt —
2FA gates critical ops via a 5-minute step-up window instead.

Layout:
    [data-tab="security"]      <- opens the Security tab
      #mfaStatusText           <- status text
      #mfaEnableBtn #mfaDisableBtn #mfaRegenerateBtn
      #mfaSetupSecret          <- TOTP secret (setup dialog)
      #mfaVerifyCode           <- 6-digit code input
      #mfaRecoveryList > li    <- 10 recovery codes
      #mfaRecoveryDoneBtn
      #mfaStepUpCode           <- step-up code input (disable)
"""

from __future__ import annotations

from typing import Self

import pyotp
from playwright.sync_api import Locator, Page, expect

from framework.step import step


class MfaSettings:
    """Drives the owner's 2FA settings: enable, verify, recovery, disable."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self._secret: str | None = None

    # ── Locators ──────────────────────────────────────────────────────

    @property
    def tab(self) -> Locator:
        """no semantic: tab without role=tab"""
        return self.page.locator('[data-tab="security"]')

    @property
    def status_text(self) -> Locator:
        """no semantic: status display, no ARIA"""
        return self.page.locator("#mfaStatusText")

    @property
    def btn_enable(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfaEnableBtn")

    @property
    def btn_disable(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfaDisableBtn")

    @property
    def setup_secret(self) -> Locator:
        """no semantic: secret display, no ARIA"""
        return self.page.locator("#mfaSetupSecret")

    @property
    def verify_code(self) -> Locator:
        """no semantic: TOTP input without label"""
        return self.page.locator("#mfaVerifyCode")

    @property
    def recovery_codes(self) -> Locator:
        """no semantic: code list items, no ARIA"""
        return self.page.locator("#mfaRecoveryList li")

    @property
    def recovery_done(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfaRecoveryDoneBtn")

    @property
    def stepup_code(self) -> Locator:
        """no semantic: TOTP input without label"""
        return self.page.locator("#mfaStepUpCode")

    # ── Methods ───────────────────────────────────────────────────────

    def open_tab(self) -> Self:
        """Click the Security tab to reveal MFA controls."""
        with step("навигация: вкладка безопасности"):
            self.tab.click()
        return self

    def enable_with_totp(self) -> None:
        """Click Enable -> read the TOTP secret -> submit a generated code."""
        with step("действие: включить 2FA через TOTP"):
            self.btn_enable.click()
            expect(self.setup_secret).to_be_visible()
            self._secret = self.setup_secret.inner_text().strip()
            self.verify_code.fill(pyotp.TOTP(self._secret).now())
            self.verify_code.press("Enter")

    def finish_recovery(self) -> None:
        """The verify step shows 10 recovery codes -- acknowledge them."""
        with step("действие: подтвердить recovery-коды"):
            expect(self.recovery_codes).to_have_count(10)
            self.recovery_done.click()

    def disable_with_stepup(self) -> None:
        """Click Disable -> step-up dialog -> submit a generated TOTP code."""
        with step("действие: отключить 2FA через step-up"):
            self.btn_disable.click()
            expect(self.stepup_code).to_be_visible()
            assert self._secret, "enable_with_totp must run before disable"  # precondition
            self.stepup_code.fill(pyotp.TOTP(self._secret).now())
            self.stepup_code.press("Enter")
