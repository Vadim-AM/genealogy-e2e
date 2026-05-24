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

from playwright.sync_api import Page, expect

from .base import BasePage


class PlatformDashboardPage(BasePage):
    URL = "/platform/dashboard"

    def __init__(self, page: Page):
        super().__init__(page)
        # ── Original metric cards (TC-PA-2 contract) ─────────────────
        self.m_tenants = page.locator("#m_tenants")  # no semantic: metric cell, no ARIA
        self.m_signups = page.locator("#m_signups")  # no semantic: metric cell, no ARIA
        self.m_signups_7 = page.locator("#m_signups7")  # no semantic: metric cell, no ARIA
        self.m_signups_30 = page.locator("#m_signups30")  # no semantic: metric cell, no ARIA
        self.m_subs = page.locator("#m_subs")  # no semantic: metric cell, no ARIA
        self.m_cap = page.locator("#m_cap")  # no semantic: metric cell, no ARIA
        self.tenants_table = page.locator("#tenants_table")  # no semantic: data table, no ARIA role
        self.acq_signup_table = page.locator("#acq_signup_table")  # no semantic: data table, no ARIA role
        self.acq_waitlist_table = page.locator("#acq_waitlist_table")  # no semantic: data table, no ARIA role
        self.grant_email = page.locator("#grant_email")  # no semantic: input without label
        self.grant_btn = page.locator("#grant_btn")  # no semantic: button without accessible name
        self.grant_msg = page.locator("#grant_msg")  # no semantic: status text, no ARIA

        # ── PR-4 funnel-detail (replaces old textContent funnel) ─────
        self.funnel_list = page.locator("#funnel_list")  # no semantic: widget container, no ARIA

        # ── PR-1 device-mix ──────────────────────────────────────────
        self.device_donut = page.locator("#donut_device")  # no semantic: chart element, no ARIA
        self.os_donut = page.locator("#donut_os")  # no semantic: chart element, no ARIA
        self.browser_donut = page.locator("#donut_browser")  # no semantic: chart element, no ARIA
        self.device_legend = page.locator("#legend_device")  # no semantic: chart legend, no ARIA
        self.conv_device_table = page.locator("#conv_device_table")  # no semantic: data table, no ARIA role
        self.device_days_select = page.locator("#device_days")  # no semantic: select without label

        # ── PR-2 activity-heatmap ────────────────────────────────────
        self.heatmap_table = page.locator("#heatmap_table")  # no semantic: data table, no ARIA role
        self.heatmap_days = page.locator("#heatmap_days")  # no semantic: select without label
        self.heatmap_tz = page.locator("#heatmap_tz")  # no semantic: select without label
        self.heatmap_legend = page.locator("#heatmap_legend")  # no semantic: legend container, no ARIA
        self.heatmap_top = page.locator("#heatmap_top")  # no semantic: summary container, no ARIA

        # ── PR-3 online + session stats ──────────────────────────────
        self.online_5m = page.locator("#online_5m")  # no semantic: metric cell, no ARIA
        self.online_1h = page.locator("#online_1h")  # no semantic: metric cell, no ARIA
        self.online_spark = page.locator("#online_spark")  # no semantic: sparkline chart, no ARIA
        self.ss_total = page.locator("#ss_total")  # no semantic: metric cell, no ARIA
        self.ss_median = page.locator("#ss_median")  # no semantic: metric cell, no ARIA
        self.ss_p75 = page.locator("#ss_p75")  # no semantic: metric cell, no ARIA
        self.ss_pages = page.locator("#ss_pages")  # no semantic: metric cell, no ARIA
        self.ss_bounce = page.locator("#ss_bounce")  # no semantic: metric cell, no ARIA
        self.session_days = page.locator("#session_days")  # no semantic: select without label

        # ── PR-4 retention + time-to-aha ─────────────────────────────
        self.cohort_table = page.locator("#cohort_table")  # no semantic: data table, no ARIA role
        self.retention_weeks = page.locator("#retention_weeks")  # no semantic: select without label
        self.tta_p25 = page.locator("#tta_p25")  # no semantic: metric cell, no ARIA
        self.tta_p50 = page.locator("#tta_p50")  # no semantic: metric cell, no ARIA
        self.tta_p75 = page.locator("#tta_p75")  # no semantic: metric cell, no ARIA
        self.tta_p95 = page.locator("#tta_p95")  # no semantic: metric cell, no ARIA
        self.tta_hist = page.locator("#tta_hist")  # no semantic: chart element, no ARIA
        self.tta_days = page.locator("#tta_days")  # no semantic: select without label

        # ── PR-5 audit log ───────────────────────────────────────────
        self.audit_table = page.locator("#audit_table")  # no semantic: data table, no ARIA role
        self.audit_filter = page.locator("#audit_action_filter")  # no semantic: select without label
        self.audit_reload = page.locator("#audit_reload")  # no semantic: button without accessible name

        # ── PR-6 alerts banner + health pills ────────────────────────
        self.alerts_banner = page.locator("#alerts_banner")  # no semantic: alert container, no ARIA role
        self.health_row = page.locator("#health_row")  # no semantic: status container, no ARIA

        # ── PR-7..9 MFA modals ───────────────────────────────────────
        self.mfa_overlay = page.locator("#mfa_overlay")  # no semantic: overlay backdrop, no ARIA
        self.mfa_setup_modal = page.locator("#mfa_modal_setup")  # no semantic: modal without role=dialog
        self.mfa_verify_modal = page.locator("#mfa_modal_verify")  # no semantic: modal without role=dialog
        self.mfa_recovery_modal = page.locator("#mfa_modal_recovery")  # no semantic: modal without role=dialog
        self.mfa_codes_modal = page.locator("#mfa_modal_codes")  # no semantic: modal without role=dialog
        self.mfa_setup_webauthn_btn = page.locator("#mfa_setup_webauthn")  # no semantic: button without accessible name
        self.mfa_setup_uri = page.locator("#mfa_setup_uri")  # no semantic: URI display, no ARIA
        self.mfa_setup_secret = page.locator("#mfa_setup_secret")  # no semantic: secret display, no ARIA
        self.mfa_setup_code = page.locator("#mfa_setup_code")  # no semantic: TOTP input without label
        self.mfa_setup_submit = page.locator("#mfa_setup_submit")  # no semantic: button without accessible name
        # no semantic: button without accessible name
        self.mfa_verify_webauthn_btn = page.locator("#mfa_verify_webauthn")
        self.mfa_verify_code = page.locator("#mfa_verify_code")  # no semantic: TOTP input without label
        self.mfa_verify_submit = page.locator("#mfa_verify_submit")  # no semantic: button without accessible name
        self.mfa_use_recovery_btn = page.locator("#mfa_use_recovery")  # no semantic: button without accessible name
        self.mfa_recovery_code_input = page.locator("#mfa_recovery_code")  # no semantic: recovery input without label
        self.mfa_recovery_submit = page.locator("#mfa_recovery_submit")  # no semantic: button without accessible name
        self.mfa_codes_list = page.locator("#mfa_codes_list")  # no semantic: code list container, no ARIA
        self.mfa_codes_done = page.locator("#mfa_codes_done")  # no semantic: button without accessible name

        # ── PR-10 step-up modal ──────────────────────────────────────
        self.stepup_modal = page.locator("#mfa_modal_stepup")  # no semantic: modal without role=dialog
        self.stepup_webauthn_btn = page.locator("#stepup_webauthn")  # no semantic: button without accessible name
        self.stepup_code = page.locator("#stepup_code")  # no semantic: TOTP input without label
        self.stepup_submit_totp = page.locator("#stepup_submit_totp")  # no semantic: button without accessible name
        self.stepup_cancel = page.locator("#stepup_cancel")  # no semantic: button without accessible name

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
        """Smoke-чек что новые секции Phase 1 присутствуют в DOM.

        Одна проверка, "все 9 виджетов на месте после bootstrap()".
        Использует soft-assert (>=3 независимых факта).
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
        # Когда MFA пройден / отключён — overlay не должен иметь класс show
        expect(self.mfa_overlay).not_to_have_class("mfa-overlay show")
