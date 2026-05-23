"""Backend invariants for superadmin platform/admin endpoints.

Superadmin-only, no journey UI — tenant listing, waitlist management,
backups, onboarding nudges, tier overrides. Step-up-gated ops
(tenant-override) run right after a fresh platform-MFA verify, which
opens the 5-minute step-up window.
"""

from __future__ import annotations

import httpx
import pyotp

from tests.api_paths import API
from tests.constants import make_email
from tests.response import expect_response
from tests.timeouts import TIMEOUTS


def test_admin_tenant_listing(superadmin_user, tenant_client):
    """Superadmin lists all tenants and looks one up by slug."""
    api = tenant_client(superadmin_user)
    listed = api.get(API.ADMIN_TENANTS)
    expect_response(listed, label="GET admin/tenants").status_ok()
    raw = listed.json()
    tenants = raw if isinstance(raw, list) else raw["items"]
    assert any(t["slug"] == superadmin_user.slug for t in tenants), \
        "superadmin's own tenant must appear in the listing"

    one = api.get(API.admin_tenant(superadmin_user.slug))
    expect_response(one, label="GET admin/tenant by slug").status_ok().json_eq("slug", superadmin_user.slug)


def test_admin_waitlist_lifecycle(superadmin_user, tenant_client, base_url):
    """A waitlist subscriber appears for superadmin, can be marked
    contacted (PATCH) and removed (DELETE)."""
    email = make_email("wl-admin")
    httpx.post(f"{base_url}{API.WAITLIST_SUBSCRIBE}", json={"email": email},
               timeout=TIMEOUTS.api_request).raise_for_status()

    api = tenant_client(superadmin_user)
    items = api.get(API.ADMIN_WAITLIST).json()
    sub = next((s for s in items if s["email"] == email), None)
    assert sub, f"subscribed email not in admin waitlist: {items}"

    api.patch(
        API.admin_waitlist_item(sub["id"]), json={"contacted": True},
    ).raise_for_status()
    api.delete(API.admin_waitlist_item(sub["id"])).raise_for_status()
    after = api.get(API.ADMIN_WAITLIST).json()
    assert not any(s["id"] == sub["id"] for s in after), \
        "deleted subscriber still listed"


def test_platform_waitlist_listing(superadmin_user, tenant_client, base_url):
    """GET /api/platform/waitlist lists waitlist subscribers for the
    superadmin. (BUG-WAITLIST-PG-002 — UnboundExecutionError — fixed
    upstream by PR #167 / 6e3565f.)"""
    email = make_email("plat-wl")
    httpx.post(f"{base_url}{API.WAITLIST_SUBSCRIBE}", json={"email": email},
               timeout=TIMEOUTS.api_request).raise_for_status()

    api = tenant_client(superadmin_user)
    r = api.get(API.PLATFORM_WAITLIST)
    expect_response(r, label="GET platform/waitlist").status_ok()
    raw = r.json()
    items = raw if isinstance(raw, list) else raw["items"]
    assert any(s.get("email") == email for s in items), \
        f"subscribed email not in platform waitlist: {items}"


def test_platform_backups_and_nudges(superadmin_user, tenant_client):
    """GET /api/platform/backups lists snapshots; POST send-onboarding-nudges
    reports how many nudges were sent."""
    api = tenant_client(superadmin_user)
    backups = api.get(API.PLATFORM_BACKUPS)
    expect_response(backups, label="GET backups").status_ok().json_has("items")

    nudges = api.post(API.PLATFORM_NUDGES)
    expect_response(nudges, label="POST nudges").status_ok().json_has("sent_count")


def test_tenant_override_lifecycle(superadmin_user, tenant_client):
    """Superadmin sets a tier override on a tenant, reads it back, deletes
    it. tenant-override POST/DELETE are step-up-gated — a fresh
    platform-MFA verify opens the window."""
    api = tenant_client(superadmin_user)
    secret = api.post(API.MFA_SETUP).json()["secret"]
    totp = pyotp.TOTP(secret)
    api.post(API.MFA_VERIFY, json={"code": totp.now()}).raise_for_status()
    api.post(
        API.MFA_STEP_UP, json={"method": "totp", "code": totp.now()},
    ).raise_for_status()

    slug = superadmin_user.slug
    api.post(API.PLATFORM_TENANT_OVERRIDE, json={
        "tenant_slug": slug, "field_name": "max_archives", "value": "999",
    }).raise_for_status()

    overrides = api.get(API.tenant_overrides(slug))
    expect_response(overrides, label="GET tenant overrides").status_ok()
    assert any(o["field_name"] == "max_archives" for o in overrides.json()["items"]), \
        "the override must be listed back"

    api.delete(API.tenant_override_field(slug, "max_archives")).raise_for_status()
    after = api.get(API.tenant_overrides(slug)).json()
    assert not any(o["field_name"] == "max_archives" for o in after["items"]), \
        "deleted override must be gone"


def test_platform_waitlist_invite_promotes_subscriber(
    superadmin_user, tenant_client, base_url,
):
    """POST /api/platform/waitlist/{id}/invite promotes a waitlist
    subscriber into a tenant + user."""
    email = make_email("wl-invite")
    httpx.post(f"{base_url}{API.WAITLIST_SUBSCRIBE}", json={"email": email},
               timeout=TIMEOUTS.api_request).raise_for_status()

    api = tenant_client(superadmin_user)
    # /api/platform/waitlist (listing) is BUG-WAITLIST-PG-002 (500) —
    # the legacy admin listing resolves the subscriber id instead.
    items = api.get(API.ADMIN_WAITLIST).json()
    sub = next(s for s in items if s["email"] == email)

    invited = api.post(API.platform_waitlist_invite(sub["id"]))
    expect_response(invited, label="waitlist invite").status_ok()
    assert invited.json()["status"] in ("invited", "already_exists"), (
        f"waitlist invite returned unexpected status: "
        f"{invited.json().get('status')!r}"
    )
