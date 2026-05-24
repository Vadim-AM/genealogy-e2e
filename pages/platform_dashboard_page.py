"""POM for /platform/dashboard — superadmin metrics, analytics widgets, MFA modals.

Покрывает PR-1..PR-10 (см. genealogy/docs/CHANGELOG.md):
  • Phase 1 widgets: device-mix, activity-heatmap, online-now, session-stats,
    retention cohort grid, time-to-aha, funnel-detail, audit-log, alerts,
    health pills.
  • Phase 2 MFA modals: setup (TouchID/TOTP), verify, recovery codes,
    step-up confirmation.

NB: PR-4 убрала старый ASCII-funnel (`#funnel`) — заменён на `#funnel_list`.
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from .base import BasePage


class PlatformDashboardPage(BasePage):
    URL = "/platform/dashboard"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Original metric cards (TC-PA-2 contract) ─────────────────

    @property
    def m_tenants(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_tenants")

    @property
    def m_signups(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_signups")

    @property
    def m_signups_7(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_signups7")

    @property
    def m_signups_30(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_signups30")

    @property
    def m_subs(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_subs")

    @property
    def m_cap(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#m_cap")

    @property
    def tenants_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#tenants_table")

    @property
    def acq_signup_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#acq_signup_table")

    @property
    def acq_waitlist_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#acq_waitlist_table")

    @property
    def grant_email(self) -> Locator:
        """no semantic: input without label"""
        return self.page.locator("#grant_email")

    @property
    def grant_btn(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#grant_btn")

    @property
    def grant_msg(self) -> Locator:
        """no semantic: status text, no ARIA"""
        return self.page.locator("#grant_msg")

    # ── PR-4 funnel-detail (replaces old textContent funnel) ─────

    @property
    def funnel_list(self) -> Locator:
        """no semantic: widget container, no ARIA"""
        return self.page.locator("#funnel_list")

    # ── PR-1 device-mix ──────────────────────────────────────────

    @property
    def device_donut(self) -> Locator:
        """no semantic: chart element, no ARIA"""
        return self.page.locator("#donut_device")

    @property
    def os_donut(self) -> Locator:
        """no semantic: chart element, no ARIA"""
        return self.page.locator("#donut_os")

    @property
    def browser_donut(self) -> Locator:
        """no semantic: chart element, no ARIA"""
        return self.page.locator("#donut_browser")

    @property
    def device_legend(self) -> Locator:
        """no semantic: chart legend, no ARIA"""
        return self.page.locator("#legend_device")

    @property
    def conv_device_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#conv_device_table")

    @property
    def device_days_select(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#device_days")

    # ── PR-2 activity-heatmap ────────────────────────────────────

    @property
    def heatmap_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#heatmap_table")

    @property
    def heatmap_days(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#heatmap_days")

    @property
    def heatmap_tz(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#heatmap_tz")

    @property
    def heatmap_legend(self) -> Locator:
        """no semantic: legend container, no ARIA"""
        return self.page.locator("#heatmap_legend")

    @property
    def heatmap_top(self) -> Locator:
        """no semantic: summary container, no ARIA"""
        return self.page.locator("#heatmap_top")

    # ── PR-3 online + session stats ──────────────────────────────

    @property
    def online_5m(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#online_5m")

    @property
    def online_1h(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#online_1h")

    @property
    def online_spark(self) -> Locator:
        """no semantic: sparkline chart, no ARIA"""
        return self.page.locator("#online_spark")

    @property
    def ss_total(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#ss_total")

    @property
    def ss_median(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#ss_median")

    @property
    def ss_p75(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#ss_p75")

    @property
    def ss_pages(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#ss_pages")

    @property
    def ss_bounce(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#ss_bounce")

    @property
    def session_days(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#session_days")

    # ── PR-4 retention + time-to-aha ─────────────────────────────

    @property
    def cohort_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#cohort_table")

    @property
    def retention_weeks(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#retention_weeks")

    @property
    def tta_p25(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#tta_p25")

    @property
    def tta_p50(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#tta_p50")

    @property
    def tta_p75(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#tta_p75")

    @property
    def tta_p95(self) -> Locator:
        """no semantic: metric cell, no ARIA"""
        return self.page.locator("#tta_p95")

    @property
    def tta_hist(self) -> Locator:
        """no semantic: chart element, no ARIA"""
        return self.page.locator("#tta_hist")

    @property
    def tta_days(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#tta_days")

    # ── PR-5 audit log ───────────────────────────────────────────

    @property
    def audit_table(self) -> Locator:
        """no semantic: data table, no ARIA role"""
        return self.page.locator("#audit_table")

    @property
    def audit_filter(self) -> Locator:
        """no semantic: select without label"""
        return self.page.locator("#audit_action_filter")

    @property
    def audit_reload(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#audit_reload")

    # ── PR-6 alerts banner + health pills ────────────────────────

    @property
    def alerts_banner(self) -> Locator:
        """no semantic: alert container, no ARIA role"""
        return self.page.locator("#alerts_banner")

    @property
    def health_row(self) -> Locator:
        """no semantic: status container, no ARIA"""
        return self.page.locator("#health_row")

    # ── PR-7..9 MFA modals ───────────────────────────────────────

    @property
    def mfa_overlay(self) -> Locator:
        """no semantic: overlay backdrop, no ARIA"""
        return self.page.locator("#mfa_overlay")

    @property
    def mfa_setup_modal(self) -> Locator:
        """no semantic: modal without role=dialog"""
        return self.page.locator("#mfa_modal_setup")

    @property
    def mfa_verify_modal(self) -> Locator:
        """no semantic: modal without role=dialog"""
        return self.page.locator("#mfa_modal_verify")

    @property
    def mfa_recovery_modal(self) -> Locator:
        """no semantic: modal without role=dialog"""
        return self.page.locator("#mfa_modal_recovery")

    @property
    def mfa_codes_modal(self) -> Locator:
        """no semantic: modal without role=dialog"""
        return self.page.locator("#mfa_modal_codes")

    @property
    def mfa_setup_webauthn_btn(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_setup_webauthn")

    @property
    def mfa_setup_uri(self) -> Locator:
        """no semantic: URI display, no ARIA"""
        return self.page.locator("#mfa_setup_uri")

    @property
    def mfa_setup_secret(self) -> Locator:
        """no semantic: secret display, no ARIA"""
        return self.page.locator("#mfa_setup_secret")

    @property
    def mfa_setup_code(self) -> Locator:
        """no semantic: TOTP input without label"""
        return self.page.locator("#mfa_setup_code")

    @property
    def mfa_setup_submit(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_setup_submit")

    @property
    def mfa_verify_webauthn_btn(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_verify_webauthn")

    @property
    def mfa_verify_code(self) -> Locator:
        """no semantic: TOTP input without label"""
        return self.page.locator("#mfa_verify_code")

    @property
    def mfa_verify_submit(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_verify_submit")

    @property
    def mfa_use_recovery_btn(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_use_recovery")

    @property
    def mfa_recovery_code_input(self) -> Locator:
        """no semantic: recovery input without label"""
        return self.page.locator("#mfa_recovery_code")

    @property
    def mfa_recovery_submit(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_recovery_submit")

    @property
    def mfa_codes_list(self) -> Locator:
        """no semantic: code list container, no ARIA"""
        return self.page.locator("#mfa_codes_list")

    @property
    def mfa_codes_done(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#mfa_codes_done")

    # ── PR-10 step-up modal ──────────────────────────────────────

    @property
    def stepup_modal(self) -> Locator:
        """no semantic: modal without role=dialog"""
        return self.page.locator("#mfa_modal_stepup")

    @property
    def stepup_webauthn_btn(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#stepup_webauthn")

    @property
    def stepup_code(self) -> Locator:
        """no semantic: TOTP input without label"""
        return self.page.locator("#stepup_code")

    @property
    def stepup_submit_totp(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#stepup_submit_totp")

    @property
    def stepup_cancel(self) -> Locator:
        """no semantic: button without accessible name"""
        return self.page.locator("#stepup_cancel")

    # ── Action helpers ───────────────────────────────────────────────

    def grant_free_license(self, email: str) -> Self:
        """Fill the grant email and click the grant button."""
        self.grant_email.fill(email)
        self.grant_btn.click()
        return self

    def soft_check_metrics_loaded(self, soft) -> None:
        """Soft-assert core metric cards and tenants table are visible."""
        for loc in (self.m_tenants, self.m_signups, self.tenants_table):
            soft(loc).to_be_visible()

    def soft_check_phase1_widgets_present(self, soft) -> None:
        """Smoke-check that new Phase 1 sections are present in the DOM.

        One check: "all 9 widgets are present after bootstrap()".
        Uses soft-assert (>=3 independent facts).
        """
        for loc in (
            self.device_donut,
            self.os_donut,
            self.browser_donut,
            self.heatmap_table,
            self.online_5m,
            self.ss_total,
            self.cohort_table,
            self.tta_hist,
            self.audit_table,
        ):
            soft(loc).to_be_visible()

    def expect_mfa_overlay_open(self) -> None:
        """Assert the MFA overlay is showing."""
        expect(self.mfa_overlay).to_have_class("mfa-overlay show")

    def expect_no_mfa_overlay(self) -> None:
        """Assert the MFA overlay is not showing."""
        expect(self.mfa_overlay).not_to_have_class("mfa-overlay show")
