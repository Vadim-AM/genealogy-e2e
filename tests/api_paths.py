"""API endpoint paths — единый source of truth для сьюта.

Использование:
    from tests.api_paths import API

    api.get(API.TREE)
    api.patch(API.person(pid), json=...)
    api.post(API.enrich(pid), json=..., timeout=TIMEOUTS.api_long)

Преимущества:
- Если backend переименует endpoint — правка в одном месте, а не
  grep+sed по 20 тестам.
- IDE'шный autocomplete вместо free-form strings.
- Контракт между e2e и backend визуально явный.
"""

from __future__ import annotations


class API:
    """Backend API endpoint paths. Все относительные (без base_url)."""

    # ── Account / auth ───────────────────────────────────────────
    SIGNUP = "/api/account/signup"
    LOGIN = "/api/account/login"
    LOGOUT = "/api/account/logout"
    VERIFY_EMAIL = "/api/account/verify-email"
    FORGOT_PASSWORD = "/api/account/forgot-password"
    RESET_PASSWORD = "/api/account/reset-password"
    ACCOUNT_ME = "/api/account/me"
    ACCOUNT_AI_CONSENT = "/api/account/me/ai-consent"
    ONBOARDING_COMPLETE = "/api/account/onboarding-complete"
    DELETE_TENANT = "/api/account/delete-tenant"

    # ── auth_v2 (also used as legacy/auth ping) ─────────────────
    AUTH_ME = "/api/auth/me"

    # ── Tenant management (invites) ──────────────────────────────
    TENANT_INVITES = "/api/account/tenant/invites"

    @staticmethod
    def tenant_invite_accept(token: str) -> str:
        return f"/api/account/tenant/invites/{token}/accept"

    # ── Tree / persons / relationships ───────────────────────────
    TREE = "/api/tree"
    PEOPLE = "/api/people"
    RELATIONSHIPS = "/api/relationships"
    SITE_CONFIG = "/api/site/config"

    @staticmethod
    def person(pid: str) -> str:
        return f"/api/people/{pid}"

    # ── Enrichment (★ Найти больше) ──────────────────────────────
    @staticmethod
    def enrich(pid: str) -> str:
        return f"/api/enrich/{pid}"

    @staticmethod
    def enrich_history(pid: str) -> str:
        return f"/api/enrich/{pid}/history"

    @staticmethod
    def enrich_jobs(job_id: str) -> str:
        return f"/api/enrich/jobs/{job_id}"

    # ── Photos ───────────────────────────────────────────────────
    TIMELINE_GEO = "/api/timeline-geo"

    # ── Health / ops ─────────────────────────────────────────────
    HEALTH = "/api/health"

    # ── Admin (legacy gates — auth_v2 миграция в процессе) ───────
    ADMIN_EXPORT_GEDCOM = "/api/admin/export-gedcom"
    ADMIN_IMPORT_GEDCOM = "/api/admin/import-gedcom"
    ADMIN_INVITES = "/api/admin/invites"

    # ── Subscription ─────────────────────────────────────────────
    SUBSCRIPTION_USAGE = "/api/account/me/subscription"

    # ── Test infra (gated by GENEALOGY_TEST_TOKEN env) ──────────
    TEST_RESET = "/api/_test/reset"
    TEST_RESET_SIGNUP_RATE = "/api/_test/reset-signup-rate"
    TEST_LAST_EMAIL = "/api/_test/last-email"
    TEST_INSTALL_MOCK_AI = "/api/_test/install-mock-ai"
    TEST_UNINSTALL_MOCK_AI = "/api/_test/uninstall-mock-ai"
