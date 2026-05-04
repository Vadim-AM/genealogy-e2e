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

from playwright.sync_api import Page, expect

from .base import BasePage


class PlatformDashboardPage(BasePage):
    URL = "/platform/dashboard"

    def __init__(self, page: Page):
        super().__init__(page)
        # ── Original metric cards (TC-PA-2 contract) ─────────────────
        self.m_tenants = page.locator("#m_tenants")
        self.m_signups = page.locator("#m_signups")
        self.m_signups_7 = page.locator("#m_signups7")
        self.m_signups_30 = page.locator("#m_signups30")
        self.m_subs = page.locator("#m_subs")
        self.m_cap = page.locator("#m_cap")
        self.tenants_table = page.locator("#tenants_table")
        self.acq_signup_table = page.locator("#acq_signup_table")
        self.acq_waitlist_table = page.locator("#acq_waitlist_table")
        self.grant_email = page.locator("#grant_email")
        self.grant_btn = page.locator("#grant_btn")
        self.grant_msg = page.locator("#grant_msg")

        # ── PR-4 funnel-detail (replaces old textContent funnel) ─────
        self.funnel_list = page.locator("#funnel_list")

        # ── PR-1 device-mix ──────────────────────────────────────────
        self.device_donut = page.locator("#donut_device")
        self.os_donut = page.locator("#donut_os")
        self.browser_donut = page.locator("#donut_browser")
        self.device_legend = page.locator("#legend_device")
        self.conv_device_table = page.locator("#conv_device_table")
        self.device_days_select = page.locator("#device_days")

        # ── PR-2 activity-heatmap ────────────────────────────────────
        self.heatmap_table = page.locator("#heatmap_table")
        self.heatmap_days = page.locator("#heatmap_days")
        self.heatmap_tz = page.locator("#heatmap_tz")
        self.heatmap_legend = page.locator("#heatmap_legend")
        self.heatmap_top = page.locator("#heatmap_top")

        # ── PR-3 online + session stats ──────────────────────────────
        self.online_5m = page.locator("#online_5m")
        self.online_1h = page.locator("#online_1h")
        self.online_spark = page.locator("#online_spark")
        self.ss_total = page.locator("#ss_total")
        self.ss_median = page.locator("#ss_median")
        self.ss_p75 = page.locator("#ss_p75")
        self.ss_pages = page.locator("#ss_pages")
        self.ss_bounce = page.locator("#ss_bounce")
        self.session_days = page.locator("#session_days")

        # ── PR-4 retention + time-to-aha ─────────────────────────────
        self.cohort_table = page.locator("#cohort_table")
        self.retention_weeks = page.locator("#retention_weeks")
        self.tta_p25 = page.locator("#tta_p25")
        self.tta_p50 = page.locator("#tta_p50")
        self.tta_p75 = page.locator("#tta_p75")
        self.tta_p95 = page.locator("#tta_p95")
        self.tta_hist = page.locator("#tta_hist")
        self.tta_days = page.locator("#tta_days")

        # ── PR-5 audit log ───────────────────────────────────────────
        self.audit_table = page.locator("#audit_table")
        self.audit_filter = page.locator("#audit_action_filter")
        self.audit_reload = page.locator("#audit_reload")

        # ── PR-6 alerts banner + health pills ────────────────────────
        self.alerts_banner = page.locator("#alerts_banner")
        self.health_row = page.locator("#health_row")

        # ── PR-7..9 MFA modals ───────────────────────────────────────
        self.mfa_overlay = page.locator("#mfa_overlay")
        self.mfa_setup_modal = page.locator("#mfa_modal_setup")
        self.mfa_verify_modal = page.locator("#mfa_modal_verify")
        self.mfa_recovery_modal = page.locator("#mfa_modal_recovery")
        self.mfa_codes_modal = page.locator("#mfa_modal_codes")
        self.mfa_setup_webauthn_btn = page.locator("#mfa_setup_webauthn")
        self.mfa_setup_uri = page.locator("#mfa_setup_uri")
        self.mfa_setup_secret = page.locator("#mfa_setup_secret")
        self.mfa_setup_code = page.locator("#mfa_setup_code")
        self.mfa_setup_submit = page.locator("#mfa_setup_submit")
        self.mfa_verify_webauthn_btn = page.locator("#mfa_verify_webauthn")
        self.mfa_verify_code = page.locator("#mfa_verify_code")
        self.mfa_verify_submit = page.locator("#mfa_verify_submit")
        self.mfa_use_recovery_btn = page.locator("#mfa_use_recovery")
        self.mfa_recovery_code_input = page.locator("#mfa_recovery_code")
        self.mfa_recovery_submit = page.locator("#mfa_recovery_submit")
        self.mfa_codes_list = page.locator("#mfa_codes_list")
        self.mfa_codes_done = page.locator("#mfa_codes_done")

        # ── PR-10 step-up modal ──────────────────────────────────────
        self.stepup_modal = page.locator("#mfa_modal_stepup")
        self.stepup_webauthn_btn = page.locator("#stepup_webauthn")
        self.stepup_code = page.locator("#stepup_code")
        self.stepup_submit_totp = page.locator("#stepup_submit_totp")
        self.stepup_cancel = page.locator("#stepup_cancel")

    # ── Action helpers ───────────────────────────────────────────────
    def grant_free_license(self, email: str) -> "PlatformDashboardPage":
        self.grant_email.fill(email)
        self.grant_btn.click()
        return self

    def soft_check_metrics_loaded(self, soft) -> None:
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
        expect(self.mfa_overlay).to_have_class("mfa-overlay show")

    def expect_no_mfa_overlay(self) -> None:
        # Когда MFA пройден / отключён — overlay не должен иметь класс show
        expect(self.mfa_overlay).not_to_have_class("mfa-overlay show")
