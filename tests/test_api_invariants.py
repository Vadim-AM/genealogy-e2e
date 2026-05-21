"""Backend invariants for endpoints with no user-facing UI journey.

The suite is journey-first: a feature is covered by a browser journey.
These endpoints are server-to-server or backend-only (tenant ops,
retention, telemetry, config, email webhooks, slug lookup) — there is no
UI a user clicks, so each test pins a MEANINGFUL backend invariant, not
a bare status code.
"""

from __future__ import annotations

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


def test_my_tenants_lists_the_owners_tenant(owner_user, tenant_client):
    """GET /api/account/my-tenants lists the tenants the user belongs to
    — at minimum their own."""
    api = tenant_client(owner_user)
    r = api.get(API.MY_TENANTS)
    r.raise_for_status()
    items = r.json()
    assert any(it["slug"] == owner_user.slug for it in items), \
        f"own tenant {owner_user.slug} missing from my-tenants: {items}"


def test_switch_tenant_to_own_tenant_succeeds(owner_user, tenant_client):
    """POST /api/account/switch-tenant to the user's own tenant keeps the
    session scoped there."""
    api = tenant_client(owner_user)
    r = api.post(API.SWITCH_TENANT, json={"tenant_slug": owner_user.slug})
    r.raise_for_status()
    assert r.json()["tenant_slug"] == owner_user.slug


def test_cookie_consent_round_trips(owner_user, tenant_client):
    """POST then GET /api/account/me/cookie-consent returns the same level
    — server-side consent persists for multi-device sync."""
    api = tenant_client(owner_user)
    api.post(API.COOKIE_CONSENT, json={"level": "necessary"}).raise_for_status()
    got = api.get(API.COOKIE_CONSENT)
    got.raise_for_status()
    assert got.json()["level"] == "necessary"


def test_config_is_public_and_carries_site_name(base_url):
    """GET /api/config is public (no auth) and exposes tenant branding."""
    r = httpx.get(f"{base_url}{API.CONFIG}", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    assert "site_name" in r.json(), f"config must carry site_name: {r.json()}"


def test_retention_offer_status_and_apply(owner_user, tenant_client):
    """GET retention-offer-status returns a boolean `show`; POST apply
    grants a 50%-off retention coupon."""
    api = tenant_client(owner_user)
    status = api.get(API.RETENTION_OFFER_STATUS)
    status.raise_for_status()
    assert isinstance(status.json()["show"], bool)

    applied = api.post(API.RETENTION_OFFER_APPLY)
    applied.raise_for_status()
    body = applied.json()
    assert body["discount_percent"] == 50, body
    assert body["coupon_code"], "apply must return a coupon code"


def test_telemetry_event_then_gdpr_erasure(owner_user, tenant_client):
    """POST a telemetry event is accepted; DELETE /api/account/me/telemetry
    purges the user's events (GDPR Art. 17 erasure)."""
    api = tenant_client(owner_user)
    posted = api.post(API.TELEMETRY_EVENTS, json={"batch": [
        {"event": "page_view", "props": {}, "ts": 0,
         "url": "/", "session_id": "e2e"},
    ]})
    posted.raise_for_status()
    assert posted.json()["received"] >= 1

    erased = api.delete(API.ACCOUNT_TELEMETRY)
    erased.raise_for_status()
    assert "deleted" in erased.json()


def test_onboarding_reset_is_idempotent(owner_user, tenant_client):
    """POST /api/account/onboarding-reset clears the onboarding flag and
    can be called twice without error."""
    api = tenant_client(owner_user)
    first = api.post(API.ONBOARDING_RESET)
    first.raise_for_status()
    assert first.json()["status"] == "reset"
    api.post(API.ONBOARDING_RESET).raise_for_status()


def test_confirm_email_change_rejects_garbage_token(owner_user, tenant_client):
    """POST /api/account/confirm-email-change with an invalid token is
    rejected — a bad token must never change an email."""
    api = tenant_client(owner_user)
    r = api.post(API.CONFIRM_EMAIL_CHANGE, json={"token": "not-a-real-token"})
    assert r.status_code == 400, f"garbage token must 400, got {r.status_code}"


def test_postmark_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/postmark-webhook without the signature
    header is rejected — inbound webhooks must be authenticated."""
    r = httpx.post(f"{base_url}{API.WEBHOOK_POSTMARK}",
                   json={"RecordType": "Bounce"}, timeout=TIMEOUTS.api_request)
    assert r.status_code == 401, f"unsigned postmark webhook: {r.status_code}"


def test_resend_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/resend-webhook without the svix signature
    is rejected."""
    r = httpx.post(f"{base_url}{API.WEBHOOK_RESEND}",
                   json={"type": "email.bounced"}, timeout=TIMEOUTS.api_request)
    assert r.status_code == 401, f"unsigned resend webhook: {r.status_code}"


def test_relationship_delete_removes_the_edge(owner_user, tenant_client):
    """DELETE /api/relationships/{id} removes a family edge — the demo
    tree seeds relationships; deleting one drops the count."""
    api = tenant_client(owner_user)
    before = api.get(API.RELATIONSHIPS).json()
    assert before, "demo tenant must seed relationships"
    rel_id = before[0]["id"]

    deleted = api.delete(API.relationship(rel_id))
    assert deleted.status_code == 204, \
        f"DELETE relationship: expected 204, got {deleted.status_code}"

    after = api.get(API.RELATIONSHIPS).json()
    assert len(after) == len(before) - 1, \
        f"relationship must be gone: {len(before)} → {len(after)}"


def test_locations_create_then_list(owner_user, tenant_client):
    """POST /api/locations creates a location; GET lists it back."""
    api = tenant_client(owner_user)
    created = api.post(API.LOCATIONS, json={
        "id": "loc-test-msk", "name": "Москва",
        "lat": 55.75, "lng": 37.62, "type": "other", "note": "",
    })
    created.raise_for_status()
    loc_id = created.json()["id"]

    listed = api.get(API.LOCATIONS)
    listed.raise_for_status()
    assert any(loc["id"] == loc_id for loc in listed.json()), \
        "created location must appear in the list"
