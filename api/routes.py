"""
Path-константы и билдеры для Genealogy API.

Использование:
    from api import routes

    api.get(routes.TREE)
    api.patch(routes.person(pid), json=...)
    api.post(routes.enrich(pid), json=..., timeout=TIMEOUTS.api_long)

Единственный source of truth для API-путей сьюта.
"""

from __future__ import annotations

# ── Account / auth ───────────────────────────────────────────────────
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
RESTORE_TENANT = "/api/account/restore-tenant"
ONBOARDING_RESET = "/api/account/onboarding-reset"
CONFIRM_EMAIL_CHANGE = "/api/account/confirm-email-change"
COOKIE_CONSENT = "/api/account/me/cookie-consent"
ACCOUNT_TELEMETRY = "/api/account/me/telemetry"

# ── Retention / telemetry / config / locations ───────────────────────
RETENTION_OFFER_STATUS = "/api/tenant/retention-offer-status"
RETENTION_OFFER_APPLY = "/api/tenant/retention-offer/apply"
TELEMETRY_EVENTS = "/api/telemetry/events"
CONFIG = "/api/config"
LOCATIONS = "/api/locations"

# ── Email webhooks (inbound, HMAC-signed) ────────────────────────────
WEBHOOK_POSTMARK = "/api/notifications/postmark-webhook"
WEBHOOK_RESEND = "/api/notifications/resend-webhook"

# ── Tenant management (invites) ──────────────────────────────────────
TENANT_INVITES = "/api/account/tenant/invites"

# ── Tree / persons / relationships ───────────────────────────────────
TREE = "/api/tree"
PEOPLE = "/api/people"
RELATIONSHIPS = "/api/relationships"
SITE_CONFIG = "/api/site/config"

# ── Enrichment (★ Найти больше) ──────────────────────────────────────
ENRICH_PREFIX = "/api/enrich/"
ENRICH_HEALTH_API_KEY = "/api/enrich/health/api-key"
ENRICH_LETTERS_SENT = "/api/enrich/letters/sent"

# ── Photos ───────────────────────────────────────────────────────────
TIMELINE_GEO = "/api/timeline-geo"

# ── Analytics ────────────────────────────────────────────────────────
ANALYTICS_LOG = "/api/analytics/log"

# ── Subscription / tenant export ─────────────────────────────────────
SUBSCRIPTION_USAGE_LEGACY = "/api/subscription/usage"
SUBSCRIPTION_CURRENT = "/api/subscription/current"
SUBSCRIPTION_CANCEL = "/api/subscription/cancel"
SUBSCRIPTION_CHECKOUT = "/api/subscription/checkout"
TENANT_EXPORT = "/api/tenant/export"

# ── Health / ops ─────────────────────────────────────────────────────
HEALTH = "/api/health"
CONFIG_FEATURES = "/api/config/features"

# ── Public pricing ───────────────────────────────────────────────────
TIERS_PUBLIC = "/api/tiers/public"

# ── Waitlist ─────────────────────────────────────────────────────────
WAITLIST_SUBSCRIBE = "/api/waitlist/subscribe"

# ── Onboarding (demo data) ───────────────────────────────────────────
ONBOARDING_CLEAR_DEMO = "/api/onboarding/clear-demo"
ONBOARDING_KEEP_DEMO = "/api/onboarding/keep-demo"

# ── Sources (historical references) ──────────────────────────────────
SOURCES = "/api/sources"
PERSON_SOURCES = "/api/person-sources"

# ── Sharing (public read-only links) ─────────────────────────────────
SHARE_CREATE = "/api/share/create"
SHARE_LIST = "/api/share/list"

# ── Legacy admin (password-gated, pre-auth_v2) ───────────────────────
ADMIN_LOGIN = "/api/admin/login"

# ── Admin (legacy gates — auth_v2 миграция в процессе) ───────────────
ADMIN_EXPORT_GEDCOM = "/api/admin/export-gedcom"
ADMIN_IMPORT_GEDCOM = "/api/admin/import-gedcom"
ADMIN_IMPORT_GEDCOM_CONFIRM = "/api/admin/import-gedcom/confirm"
UPLOAD_PHOTO = "/api/admin/upload-photo"
ADMIN_TENANTS = "/api/admin/tenants"
ADMIN_WAITLIST = "/api/admin/waitlist"

# ── Platform ops (superadmin) ────────────────────────────────────────
PLATFORM_WAITLIST = "/api/platform/waitlist"
PLATFORM_BACKUPS = "/api/platform/backups"
PLATFORM_NUDGES = "/api/platform/send-onboarding-nudges"
PLATFORM_TENANT_OVERRIDE = "/api/platform/tenant-override"
PLATFORM_EXPIRE_SUBSCRIPTIONS = "/api/platform/expire-subscriptions"

# ── Test infra (gated by GENEALOGY_TEST_TOKEN env) ───────────────────
TEST_RESET = "/api/_test/reset"
TEST_RESET_SIGNUP_RATE = "/api/_test/reset-signup-rate"
TEST_LAST_EMAIL = "/api/_test/last-email"
TEST_INSTALL_MOCK_AI = "/api/_test/install-mock-ai"
TEST_UNINSTALL_MOCK_AI = "/api/_test/uninstall-mock-ai"
TEST_SET_PLATFORM_SETTING = "/api/_test/set-platform-setting"

# ── Platform superadmin (PR-1..10) ───────────────────────────────────
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

# ── User MFA (account-level 2FA) ─────────────────────────────────────
USER_MFA_SETUP = "/api/account/mfa/setup"
USER_MFA_VERIFY = "/api/account/mfa/verify"
USER_MFA_DISABLE = "/api/account/mfa/disable"
USER_MFA_STATUS = "/api/account/mfa/status"
USER_MFA_STEP_UP = "/api/account/mfa/step-up"
USER_MFA_RECOVERY_COUNT = "/api/account/mfa/recovery-codes/count"
USER_MFA_RECOVERY_REGEN = "/api/account/mfa/recovery-codes/regenerate"
USER_MFA_RECOVERY_REDEEM = "/api/account/mfa/recovery-redeem"

# ── Platform MFA (PR-7..10) ──────────────────────────────────────────
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


# ── Билдеры (параметризованные пути) ────────────────────────────────


def relationship(rel_id: str) -> str:
    """Return path for a specific relationship."""
    return f"/api/relationships/{rel_id}"


def tenant_invite(token: str) -> str:
    """Return path for a specific tenant invite."""
    return f"/api/account/tenant/invites/{token}"


def tenant_invite_accept(token: str) -> str:
    """Return path to accept a tenant invite."""
    return f"/api/account/tenant/invites/{token}/accept"


def person(pid: str) -> str:
    """Return path for a specific person."""
    return f"/api/people/{pid}"


def person_by_slug(slug: str) -> str:
    """Return path for person lookup by display slug."""
    return f"/api/people/by-display-slug/{slug}"


def enrich(pid: str) -> str:
    """Return path for person enrichment."""
    return f"/api/enrich/{pid}"


def enrich_history(pid: str) -> str:
    """Return path for person enrichment history."""
    return f"/api/enrich/{pid}/history"


def enrich_jobs(job_id: str) -> str:
    """Return path for a specific enrichment job."""
    return f"/api/enrich/jobs/{job_id}"


def enrich_acceptances(pid: str) -> str:
    """Return path for person enrichment acceptances."""
    return f"/api/enrich/{pid}/acceptances"


def enrich_accept(pid: str) -> str:
    """Return path to accept enrichment results."""
    return f"/api/enrich/{pid}/accept"


def enrich_revert(acceptance_id: int) -> str:
    """Return path to revert an enrichment acceptance."""
    return f"/api/enrich/acceptances/{acceptance_id}/revert"


def enrich_stream(job_id: str) -> str:
    """Return path for enrichment job SSE stream."""
    return f"/api/enrich/jobs/{job_id}/stream"


def enrich_cache(enrichment_id: int) -> str:
    """Return path for enrichment cache entry."""
    return f"/api/enrich/cache/{enrichment_id}"


def enrich_feedback(pid: str) -> str:
    """Return path for enrichment feedback."""
    return f"/api/enrich/{pid}/feedback"


def source(source_id: str) -> str:
    """Return path for a specific source."""
    return f"/api/sources/{source_id}"


def person_sources(person_id: str) -> str:
    """Return path for sources linked to a person."""
    return f"/api/people/{person_id}/sources"


def person_source_link(link_id: int) -> str:
    """Return path for a specific person-source link."""
    return f"/api/person-sources/{link_id}"


def share(share_id: int) -> str:
    """Return path for a specific share link."""
    return f"/api/share/{share_id}"


def share_view(token: str) -> str:
    """Return path to view a shared tree by token."""
    return f"/api/share/view/{token}"


def photo(photo_id: str) -> str:
    """Return path for a specific admin photo."""
    return f"/api/admin/photos/{photo_id}"


def admin_tenant(slug: str) -> str:
    """Return path for a specific admin tenant."""
    return f"/api/admin/tenants/{slug}"


def admin_waitlist_item(subscriber_id: int) -> str:
    """Return path for a specific admin waitlist item."""
    return f"/api/admin/waitlist/{subscriber_id}"


def tenant_overrides(slug: str) -> str:
    """Return path for tenant overrides by slug."""
    return f"/api/platform/tenant-overrides/{slug}"


def tenant_override_field(slug: str, field: str) -> str:
    """Return path for a specific tenant override field."""
    return f"/api/platform/tenant-override/{slug}/{field}"


def platform_waitlist_invite(subscriber_id: int) -> str:
    """Return path to invite a platform waitlist subscriber."""
    return f"/api/platform/waitlist/{subscriber_id}/invite"


def webauthn_credential(credential_pk: int) -> str:
    """Return path for a specific WebAuthn credential."""
    return f"/api/platform/mfa/webauthn/{credential_pk}"


def tier_config(tier_name: str) -> str:
    """Return path for a specific tier configuration."""
    return f"/api/platform/tier-config/{tier_name}"
