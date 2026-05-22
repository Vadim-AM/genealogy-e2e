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
    ACCOUNT_EMAIL = "/api/account/me/email"
    ONBOARDING_COMPLETE = "/api/account/onboarding-complete"
    DELETE_TENANT = "/api/account/delete-tenant"
    MY_TENANTS = "/api/account/my-tenants"
    SWITCH_TENANT = "/api/account/switch-tenant"
    ONBOARDING_RESET = "/api/account/onboarding-reset"
    CONFIRM_EMAIL_CHANGE = "/api/account/confirm-email-change"
    COOKIE_CONSENT = "/api/account/me/cookie-consent"
    ACCOUNT_TELEMETRY = "/api/account/me/telemetry"

    # ── Retention / telemetry / config / locations ───────────────
    RETENTION_OFFER_STATUS = "/api/tenant/retention-offer-status"
    RETENTION_OFFER_APPLY = "/api/tenant/retention-offer/apply"
    TELEMETRY_EVENTS = "/api/telemetry/events"
    CONFIG = "/api/config"
    LOCATIONS = "/api/locations"

    @staticmethod
    def relationship(rel_id: str) -> str:
        return f"/api/relationships/{rel_id}"

    # ── Email webhooks (inbound, HMAC-signed) ────────────────────
    WEBHOOK_POSTMARK = "/api/notifications/postmark-webhook"
    WEBHOOK_RESEND = "/api/notifications/resend-webhook"

    # ── Tenant management (invites) ──────────────────────────────
    TENANT_INVITES = "/api/account/tenant/invites"

    @staticmethod
    def tenant_invite(token: str) -> str:
        return f"/api/account/tenant/invites/{token}"

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

    @staticmethod
    def enrich_acceptances(pid: str) -> str:
        return f"/api/enrich/{pid}/acceptances"

    @staticmethod
    def enrich_accept(pid: str) -> str:
        return f"/api/enrich/{pid}/accept"

    @staticmethod
    def enrich_revert(acceptance_id: int) -> str:
        return f"/api/enrich/acceptances/{acceptance_id}/revert"

    @staticmethod
    def enrich_stream(job_id: str) -> str:
        return f"/api/enrich/jobs/{job_id}/stream"

    @staticmethod
    def enrich_cache(enrichment_id: int) -> str:
        return f"/api/enrich/cache/{enrichment_id}"

    ENRICH_HEALTH_API_KEY = "/api/enrich/health/api-key"

    # ── Photos ───────────────────────────────────────────────────
    TIMELINE_GEO = "/api/timeline-geo"

    # ── Analytics ────────────────────────────────────────────────
    ANALYTICS_LOG = "/api/analytics/log"

    # ── Subscription / tenant export ─────────────────────────────
    SUBSCRIPTION_USAGE_LEGACY = "/api/subscription/usage"
    SUBSCRIPTION_CURRENT = "/api/subscription/current"
    SUBSCRIPTION_CANCEL = "/api/subscription/cancel"
    TENANT_EXPORT = "/api/tenant/export"

    # ── Health / ops ─────────────────────────────────────────────
    HEALTH = "/api/health"
    CONFIG_FEATURES = "/api/config/features"

    # ── Public pricing ───────────────────────────────────────────
    TIERS_PUBLIC = "/api/tiers/public"

    # ── Waitlist ─────────────────────────────────────────────────
    # Exercised via the UI journey in tests/ui/test_waitlist.py (form
    # submit) — kept here so the coverage gate counts it as covered.
    WAITLIST_SUBSCRIBE = "/api/waitlist/subscribe"

    # ── Onboarding (demo data) ───────────────────────────────────
    ONBOARDING_CLEAR_DEMO = "/api/onboarding/clear-demo"
    ONBOARDING_KEEP_DEMO = "/api/onboarding/keep-demo"

    # ── Sources (historical references) ──────────────────────────
    SOURCES = "/api/sources"
    PERSON_SOURCES = "/api/person-sources"

    @staticmethod
    def source(source_id: str) -> str:
        return f"/api/sources/{source_id}"

    @staticmethod
    def person_sources(person_id: str) -> str:
        return f"/api/people/{person_id}/sources"

    @staticmethod
    def person_source_link(link_id: int) -> str:
        return f"/api/person-sources/{link_id}"

    # ── Sharing (public read-only links) ─────────────────────────
    SHARE_CREATE = "/api/share/create"
    SHARE_LIST = "/api/share/list"

    @staticmethod
    def share(share_id: int) -> str:
        return f"/api/share/{share_id}"

    # /api/share/view/{token} deliberately absent — broken on PG
    # (BUG-SHARE-PG-001); it stays in test_api_coverage KNOWN_GAPS.

    # ── Legacy admin (password-gated, pre-auth_v2) ───────────────
    ADMIN_LOGIN = "/api/admin/login"

    # ── Admin (legacy gates — auth_v2 миграция в процессе) ───────
    ADMIN_EXPORT_GEDCOM = "/api/admin/export-gedcom"
    ADMIN_IMPORT_GEDCOM = "/api/admin/import-gedcom"
    ADMIN_IMPORT_GEDCOM_CONFIRM = "/api/admin/import-gedcom/confirm"
    UPLOAD_PHOTO = "/api/admin/upload-photo"
    ADMIN_TENANTS = "/api/admin/tenants"

    @staticmethod
    def photo(photo_id: str) -> str:
        return f"/api/admin/photos/{photo_id}"
    ADMIN_WAITLIST = "/api/admin/waitlist"

    @staticmethod
    def admin_tenant(slug: str) -> str:
        return f"/api/admin/tenants/{slug}"

    @staticmethod
    def admin_waitlist_item(subscriber_id: int) -> str:
        return f"/api/admin/waitlist/{subscriber_id}"

    # ── Platform ops (superadmin) ────────────────────────────────
    PLATFORM_BACKUPS = "/api/platform/backups"
    PLATFORM_NUDGES = "/api/platform/send-onboarding-nudges"
    PLATFORM_TENANT_OVERRIDE = "/api/platform/tenant-override"

    @staticmethod
    def tenant_overrides(slug: str) -> str:
        return f"/api/platform/tenant-overrides/{slug}"

    @staticmethod
    def tenant_override_field(slug: str, field: str) -> str:
        return f"/api/platform/tenant-override/{slug}/{field}"

    @staticmethod
    def platform_waitlist_invite(subscriber_id: int) -> str:
        return f"/api/platform/waitlist/{subscriber_id}/invite"

    # ── Test infra (gated by GENEALOGY_TEST_TOKEN env) ──────────
    TEST_RESET = "/api/_test/reset"
    TEST_RESET_SIGNUP_RATE = "/api/_test/reset-signup-rate"
    TEST_LAST_EMAIL = "/api/_test/last-email"
    TEST_INSTALL_MOCK_AI = "/api/_test/install-mock-ai"
    TEST_UNINSTALL_MOCK_AI = "/api/_test/uninstall-mock-ai"
    TEST_SET_PLATFORM_SETTING = "/api/_test/set-platform-setting"

    # ── Platform superadmin (PR-1..10) ───────────────────────────
    PLATFORM_METRICS = "/api/platform/metrics"
    PLATFORM_TENANTS = "/api/platform/tenants"
    PLATFORM_USERS = "/api/platform/users"
    PLATFORM_GEO_STATS = "/api/platform/users/geo-stats"
    PLATFORM_FUNNEL = "/api/platform/funnel"
    PLATFORM_ACQUISITION = "/api/platform/acquisition"
    PLATFORM_RAGE_SPOTS = "/api/platform/rage-spots"
    PLATFORM_DEVICE_MIX = "/api/platform/device-mix"
    PLATFORM_ACTIVITY_HEATMAP = "/api/platform/activity-heatmap"
    PLATFORM_ONLINE_NOW = "/api/platform/online-now"
    PLATFORM_SESSION_STATS = "/api/platform/session-stats"
    PLATFORM_RETENTION = "/api/platform/retention"
    PLATFORM_TIME_TO_AHA = "/api/platform/time-to-aha"
    PLATFORM_FUNNEL_DETAIL = "/api/platform/funnel-detail"
    PLATFORM_AUDIT_LOG = "/api/platform/audit-log"
    PLATFORM_ALERTS = "/api/platform/alerts"
    PLATFORM_HEALTH = "/api/platform/health"
    PLATFORM_FREE_LICENSE_GRANT = "/api/platform/free-license-grant"
    PLATFORM_BACKUP_SNAPSHOT = "/api/platform/backup-snapshot"
    PLATFORM_CLEANUP_DELETED = "/api/platform/cleanup-deleted"
    PLATFORM_TIER_CONFIG = "/api/platform/tier-config"
    PLATFORM_SETTINGS = "/api/platform/settings"

    # ── User MFA (account-level 2FA) ─────────────────────────────
    USER_MFA_SETUP = "/api/account/mfa/setup"
    USER_MFA_VERIFY = "/api/account/mfa/verify"
    USER_MFA_DISABLE = "/api/account/mfa/disable"
    USER_MFA_STATUS = "/api/account/mfa/status"
    USER_MFA_STEP_UP = "/api/account/mfa/step-up"
    USER_MFA_RECOVERY_COUNT = "/api/account/mfa/recovery-codes/count"
    USER_MFA_RECOVERY_REGEN = "/api/account/mfa/recovery-codes/regenerate"
    USER_MFA_RECOVERY_REDEEM = "/api/account/mfa/recovery-redeem"

    # ── Platform MFA (PR-7..10) ──────────────────────────────────
    MFA_SETUP = "/api/platform/mfa/setup"
    MFA_VERIFY = "/api/platform/mfa/verify"
    MFA_STATUS = "/api/platform/mfa/status"
    MFA_RECOVERY_REGENERATE = "/api/platform/mfa/recovery-codes/regenerate"
    MFA_RECOVERY_REDEEM = "/api/platform/mfa/recovery-redeem"
    MFA_RECOVERY_COUNT = "/api/platform/mfa/recovery-codes/count"
    MFA_STEP_UP = "/api/platform/mfa/step-up"
    WEBAUTHN_LIST = "/api/platform/mfa/webauthn"
    WEBAUTHN_REGISTER_BEGIN = "/api/platform/mfa/webauthn/register/begin"
    WEBAUTHN_REGISTER_COMPLETE = "/api/platform/mfa/webauthn/register/complete"
    WEBAUTHN_AUTH_BEGIN = "/api/platform/mfa/webauthn/authenticate/begin"
    WEBAUTHN_AUTH_COMPLETE = "/api/platform/mfa/webauthn/authenticate/complete"

    @staticmethod
    def webauthn_credential(credential_pk: int) -> str:
        return f"/api/platform/mfa/webauthn/{credential_pk}"

    @staticmethod
    def tier_config(tier_name: str) -> str:
        return f"/api/platform/tier-config/{tier_name}"
