"""Backend invariants for endpoints with no user-facing UI journey.

The suite is journey-first: a feature is covered by a browser journey.
These endpoints are server-to-server or backend-only (tenant ops,
retention, telemetry, config, email webhooks, slug lookup) — there is no
UI a user clicks, so each test pins a MEANINGFUL backend invariant, not
a bare status code.
"""

from __future__ import annotations

import base64

import httpx

import allure

from tests.api_paths import API
from tests.messages import TestData
from tests.response import expect_response
from tests.timeouts import TIMEOUTS

# Minimal valid 1×1 transparent PNG — for the photo-upload invariant.
_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42m"
    "P8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@allure.title("API: my-tenants содержит собственный тенант владельца")
def test_my_tenants_lists_the_owners_tenant(owner_user, tenant_client):
    """GET /api/account/my-tenants lists the tenants the user belongs to
    — at minimum their own."""
    api = tenant_client(owner_user)
    r = api.get(API.MY_TENANTS)
    expect_response(r, label="my-tenants").status_ok()
    items = r.json()
    assert any(it["slug"] == owner_user.slug for it in items), \
        f"own tenant {owner_user.slug} missing from my-tenants: {items}"


@allure.title("API: переключение на свой тенант проходит успешно")
def test_switch_tenant_to_own_tenant_succeeds(owner_user, tenant_client):
    """POST /api/account/switch-tenant to the user's own tenant keeps the
    session scoped there."""
    api = tenant_client(owner_user)
    r = api.post(API.SWITCH_TENANT, json={"tenant_slug": owner_user.slug})
    expect_response(r, label="switch-tenant").status_ok().json_eq("tenant_slug", owner_user.slug)


@allure.title("API: cookie-consent сохраняется и читается обратно")
def test_cookie_consent_round_trips(owner_user, tenant_client):
    """POST then GET /api/account/me/cookie-consent returns the same level
    — server-side consent persists for multi-device sync."""
    api = tenant_client(owner_user)
    expect_response(
        api.post(API.COOKIE_CONSENT, json={"level": "necessary"}),
        label="cookie-consent set",
    ).status_ok()
    got = api.get(API.COOKIE_CONSENT)
    expect_response(got, label="cookie-consent get").status_ok().json_eq("level", "necessary")


@allure.title("API: /api/config публичен и содержит site_name")
def test_config_is_public_and_carries_site_name(base_url):
    """GET /api/config is public (no auth) and exposes tenant branding."""
    r = httpx.get(f"{base_url}{API.CONFIG}", timeout=TIMEOUTS.api_request)
    expect_response(r, label="config").status_ok().json_has("site_name")


@allure.title("API: retention-offer выдаёт 50%-скидку при применении")
def test_retention_offer_status_and_apply(owner_user, tenant_client):
    """GET retention-offer-status returns a boolean `show`; POST apply
    grants a 50%-off retention coupon."""
    api = tenant_client(owner_user)
    status = api.get(API.RETENTION_OFFER_STATUS)
    expect_response(status, label="retention-offer-status").status_ok().json_has("show")
    assert isinstance(status.json()["show"], bool), \
        f"retention-offer show must be bool, got {type(status.json()['show']).__name__}"

    applied = api.post(API.RETENTION_OFFER_APPLY)
    expect_response(applied, label="retention-offer-apply").status_ok().json_eq("discount_percent", 50)
    assert applied.json()["coupon_code"], "apply must return a coupon code"


@allure.title("API: телеметрия принимается, GDPR-удаление стирает её")
def test_telemetry_event_then_gdpr_erasure(owner_user, tenant_client):
    """POST a telemetry event is accepted; DELETE /api/account/me/telemetry
    purges the user's events (GDPR Art. 17 erasure)."""
    api = tenant_client(owner_user)
    posted = api.post(API.TELEMETRY_EVENTS, json={"batch": [
        {"event": "page_view", "props": {}, "ts": 0,
         "url": "/", "session_id": "e2e"},
    ]})
    expect_response(posted, label="telemetry post").status_ok().json_has("received")
    assert posted.json()["received"] >= 1, \
        f"telemetry must accept >= 1 event, got {posted.json()['received']}"

    erased = api.delete(API.ACCOUNT_TELEMETRY)
    expect_response(erased, label="GDPR erasure").status_ok().json_has("deleted")


@allure.title("API: сброс onboarding идемпотентен (два вызова подряд)")
def test_onboarding_reset_is_idempotent(owner_user, tenant_client):
    """POST /api/account/onboarding-reset clears the onboarding flag and
    can be called twice without error."""
    api = tenant_client(owner_user)
    first = api.post(API.ONBOARDING_RESET)
    expect_response(first, label="onboarding-reset").status_ok().json_eq("status", "reset")
    expect_response(api.post(API.ONBOARDING_RESET), label="onboarding-reset idempotent").status_ok()


@allure.title("API: поддельный токен смены email отклоняется (400)")
def test_confirm_email_change_rejects_garbage_token(owner_user, tenant_client):
    """POST /api/account/confirm-email-change with an invalid token is
    rejected — a bad token must never change an email."""
    api = tenant_client(owner_user)
    r = api.post(API.CONFIRM_EMAIL_CHANGE, json={"token": "not-a-real-token"})
    expect_response(r, label="confirm-email-change garbage token").status(400)


@allure.title("API: Postmark webhook без подписи отклоняется (401)")
def test_postmark_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/postmark-webhook without the signature
    header is rejected — inbound webhooks must be authenticated."""
    r = httpx.post(f"{base_url}{API.WEBHOOK_POSTMARK}",
                   json={"RecordType": "Bounce"}, timeout=TIMEOUTS.api_request)
    expect_response(r, label="unsigned postmark webhook").status(401)


@allure.title("API: Resend webhook без подписи отклоняется (401)")
def test_resend_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/resend-webhook without the svix signature
    is rejected."""
    r = httpx.post(f"{base_url}{API.WEBHOOK_RESEND}",
                   json={"type": "email.bounced"}, timeout=TIMEOUTS.api_request)
    expect_response(r, label="unsigned resend webhook").status(401)


@allure.title("API: удаление связи убирает ребро из дерева")
def test_relationship_delete_removes_the_edge(owner_user, tenant_client):
    """DELETE /api/relationships/{id} removes a family edge — the demo
    tree seeds relationships; deleting one drops the count."""
    api = tenant_client(owner_user)
    before = api.get(API.RELATIONSHIPS).json()
    assert before, "demo tenant must seed relationships"
    rel_id = before[0]["id"]

    deleted = api.delete(API.relationship(rel_id))
    expect_response(deleted, label="DELETE relationship").status(204)

    after = api.get(API.RELATIONSHIPS).json()
    assert len(after) == len(before) - 1, \
        f"relationship must be gone: {len(before)} → {len(after)}"


@allure.title("API: отмена подписки на бесплатном тарифе отклоняется (400)")
def test_subscription_current_and_cancel(owner_user, tenant_client):
    """GET /api/subscription/current reports the tenant's tier; POST
    cancel on a free tenant (no paid subscription) is rejected 400 —
    there is nothing to cancel."""
    api = tenant_client(owner_user)
    current = api.get(API.SUBSCRIPTION_CURRENT)
    expect_response(current, label="subscription current").status_ok().json_has("tenant", "subscription")
    assert current.json()["tenant"]["tier"] == "free", \
        f"new tenant tier: expected 'free', got {current.json()['tenant']['tier']!r}"
    assert current.json()["subscription"] is None, \
        f"new tenant subscription must be None, got {current.json()['subscription']!r}"

    cancelled = api.post(API.SUBSCRIPTION_CANCEL)
    expect_response(cancelled, label="cancel without subscription").status(400)


@allure.title("API: владелец отзывает выданное приглашение")
def test_invite_revoke(owner_user, tenant_client, create_invite):
    """Owner issues a tenant invite, then revokes it by token —
    DELETE /api/account/tenant/invites/{token} reports it revoked."""
    create_invite(owner_user, role="editor", name="Гость")
    api = tenant_client(owner_user)
    pending = api.get(API.TENANT_INVITES)
    expect_response(pending, label="tenant invites").status_ok()
    items = pending.json()
    items = items if isinstance(items, list) else items["items"]
    assert items, "issued invite must be pending"
    token = items[0]["token"]

    revoked = api.delete(API.tenant_invite(token))
    expect_response(revoked, label="invite revoke").status_ok().json_eq("status", "revoked")


@allure.title("API: загрузка фото и установка подписи к нему")
def test_photo_upload_and_caption(owner_user, tenant_client):
    """Owner uploads a photo to a person, then sets its caption — the
    upload links a Photo row and PATCH updates its caption."""
    api = tenant_client(owner_user)
    uploaded = api.post(
        API.UPLOAD_PHOTO,
        params={"person_id": TestData.DEMO_PERSON_ID},
        files={"file": ("e2e.png", _PNG_1PX, "image/png")},
    )
    expect_response(uploaded, label="photo upload").status_ok().json_has("photo_id")
    photo_id = uploaded.json()["photo_id"]

    patched = api.patch(API.photo(photo_id), json={"caption": "Тестовая подпись"})
    expect_response(patched, label="photo caption").status_ok().json_eq("caption", "Тестовая подпись")


@allure.title("API: checkout без платёжного провайдера даёт pending")
def test_subscription_checkout_pending_without_payment_provider(
    owner_user, tenant_client,
):
    """POST /api/subscription/checkout for a paid tier resolves to a
    `pending_payment_provider` status — no payment provider is wired in
    test mode, but the endpoint handles it cleanly (no 500)."""
    api = tenant_client(owner_user)
    r = api.post(API.SUBSCRIPTION_CHECKOUT, json={"tier": "pro"})
    expect_response(r, label="subscription checkout").status_ok().json_eq("status", "pending_payment_provider")


@allure.title("API: персона находится по display_slug")
def test_person_by_display_slug_resolves(owner_user, tenant_client):
    """A person created with a display_slug is resolvable by that slug —
    GET /api/people/by-display-slug/{slug} returns the same person."""
    api = tenant_client(owner_user)
    slug = "e2e-slug-person"
    created = api.post(
        API.PEOPLE, json={"name": "Слаг Тест", "display_slug": slug},
    )
    expect_response(created, label="create person with slug").status_ok().json_has("id")
    pid = created.json()["id"]

    resolved = api.get(API.person_by_slug(slug))
    expect_response(resolved, label="by-display-slug").status_ok().json_eq("id", pid)


@allure.title("API: удалённый тенант восстанавливается в grace-период")
def test_tenant_delete_then_restore(
    owner_user, tenant_client, login_existing, base_url,
):
    """Owner soft-deletes their tenant; after re-login (delete kills the
    session) the tenant is restored within the 30-day grace period."""
    api = tenant_client(owner_user)
    expect_response(
        api.post(API.DELETE_TENANT, json={"confirm_slug": owner_user.slug}),
        label="delete tenant",
    ).status_ok()

    cookies = login_existing(owner_user.email, owner_user.password)
    restored = httpx.post(
        f"{base_url}{API.RESTORE_TENANT}",
        json={"tenant_slug": owner_user.slug},
        cookies=cookies,
        headers={"Origin": base_url},
        timeout=TIMEOUTS.api_request,
    )
    expect_response(restored, label="tenant restore").status_ok().json_eq("status", "restored")


@allure.title("API: создание локации и её появление в списке")
def test_locations_create_then_list(owner_user, tenant_client):
    """POST /api/locations creates a location; GET lists it back."""
    api = tenant_client(owner_user)
    created = api.post(API.LOCATIONS, json={
        "id": "loc-test-msk", "name": "Москва",
        "lat": 55.75, "lng": 37.62, "type": "other", "note": "",
    })
    expect_response(created, label="create location").status_ok().json_has("id")
    loc_id = created.json()["id"]

    listed = api.get(API.LOCATIONS)
    expect_response(listed, label="list locations").status_ok()
    assert any(loc["id"] == loc_id for loc in listed.json()), \
        "created location must appear in the list"
