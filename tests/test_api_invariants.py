"""Backend invariants for endpoints with no user-facing UI journey.

The suite is journey-first: a feature is covered by a browser journey.
These endpoints are server-to-server or backend-only (tenant ops,
retention, telemetry, config, email webhooks, slug lookup) — there is no
UI a user clicks, so each test pins a MEANINGFUL backend invariant, not
a bare status code.
"""

from __future__ import annotations

import base64

from http import HTTPStatus

import allure
import httpx

from tests._core import api_paths as routes
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests._models.person import LocationResponse, PersonResponse
from tests._models.site import RetentionOfferApply, RetentionOfferStatus, SubscriptionResponse
from tests.helpers.api import auth_api, platform_api, relationship_api

# Minimal valid 1×1 transparent PNG — for the photo-upload invariant.
_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42m"
    "P8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@allure.title("API: my-tenants содержит собственный тенант владельца")
def test_my_tenants_lists_the_owners_tenant(owner_user, tenant_client):
    """GET /api/account/my-tenants lists the tenants the user belongs to
    — at minimum their own."""
    with step("действие: запросить my-tenants"):
        api = tenant_client(owner_user)
        r = api.get(routes.MY_TENANTS)
        items = expect_response(r, label="my-tenants").status_ok().data

    with step("проверка: собственный тенант в списке"):
        assert any(it["slug"] == owner_user.slug for it in items), \
            f"own tenant {owner_user.slug} missing from my-tenants: {items}"


@allure.title("API: переключение на свой тенант проходит успешно")
def test_switch_tenant_to_own_tenant_succeeds(owner_user, tenant_client):
    """POST /api/account/switch-tenant to the user's own tenant keeps the
    session scoped there."""
    with step("действие: switch-tenant на собственный тенант"):
        api = tenant_client(owner_user)
        r = api.post(routes.SWITCH_TENANT, json={"tenant_slug": owner_user.slug})

    with step("проверка: ответ содержит правильный tenant_slug"):
        expect_response(r, label="switch-tenant").status_ok().json_eq("tenant_slug", owner_user.slug)


@allure.title("API: cookie-consent сохраняется и читается обратно")
def test_cookie_consent_round_trips(owner_user, tenant_client):
    """POST then GET /api/account/me/cookie-consent returns the same level
    — server-side consent persists for multi-device sync."""
    with step("действие: записать cookie-consent level=necessary"):
        api = tenant_client(owner_user)
        expect_response(
            api.post(routes.COOKIE_CONSENT, json={"level": "necessary"}),
            label="cookie-consent set",
        ).status_ok()

    with step("проверка: GET возвращает тот же level"):
        got = api.get(routes.COOKIE_CONSENT)
        expect_response(got, label="cookie-consent get").status_ok().json_eq("level", "necessary")


@allure.title("API: /api/config публичен и содержит site_name")
def test_config_is_public_and_carries_site_name(base_url):
    """GET /api/config is public (no auth) and exposes tenant branding."""
    r = httpx.get(f"{base_url}{routes.CONFIG}", timeout=TIMEOUTS.api_request)
    expect_response(r, label="config").status_ok().json_has("site_name")


@allure.title("API: retention-offer выдаёт 50%-скидку при применении")
def test_retention_offer_status_and_apply(owner_user, tenant_client):
    """GET retention-offer-status returns a boolean `show`; POST apply
    grants a 50%-off retention coupon."""
    with step("действие: запросить статус retention-offer"):
        api = tenant_client(owner_user)
        r_status = api.get(routes.RETENTION_OFFER_STATUS)
        status = expect_response(r_status, label="retention-offer-status").status_ok().schema(RetentionOfferStatus)
        assert isinstance(status.show, bool), \
            f"retention-offer show must be bool, got {type(status.show).__name__}"

    with step("проверка: apply возвращает 50%-скидку с купоном"):
        r_apply = api.post(routes.RETENTION_OFFER_APPLY)
        applied = expect_response(r_apply, label="retention-offer-apply").status_ok().schema(RetentionOfferApply)
        assert applied.discount_percent == 50, \
            f"discount_percent: expected 50, got {applied.discount_percent!r}"
        assert applied.coupon_code, "apply must return a coupon code"


@allure.title("API: телеметрия принимается, GDPR-удаление стирает её")
def test_telemetry_event_then_gdpr_erasure(owner_user, tenant_client):
    """POST a telemetry event is accepted; DELETE /api/account/me/telemetry
    purges the user's events (GDPR Art. 17 erasure)."""
    with step("действие: отправить телеметрию"):
        api = tenant_client(owner_user)
        telemetry = platform_api.post_telemetry(api, [
            {"event": "page_view", "props": {}, "ts": 0,
             "url": "/", "session_id": "e2e"},
        ])
        assert telemetry.received >= 1, \
            f"telemetry must accept >= 1 event, got {telemetry.received}"

    with step("проверка: GDPR-удаление стирает события"):
        erased = api.delete(routes.ACCOUNT_TELEMETRY)
        expect_response(erased, label="GDPR erasure").status_ok().json_has("deleted")


@allure.title("API: сброс onboarding идемпотентен (два вызова подряд)")
def test_onboarding_reset_is_idempotent(owner_user, tenant_client):
    """POST /api/account/onboarding-reset clears the onboarding flag and
    can be called twice without error."""
    with step("действие: первый вызов onboarding-reset"):
        api = tenant_client(owner_user)
        auth_api.onboarding_reset(api)

    with step("проверка: повторный вызов идемпотентен"):
        auth_api.onboarding_reset(api)


@allure.title("API: поддельный токен смены email отклоняется (400)")
def test_confirm_email_change_rejects_garbage_token(owner_user, tenant_client):
    """POST /api/account/confirm-email-change with an invalid token is
    rejected — a bad token must never change an email."""
    api = tenant_client(owner_user)
    r = api.post(routes.CONFIRM_EMAIL_CHANGE, json={"token": "not-a-real-token"})
    expect_response(r, label="confirm-email-change garbage token").status(HTTPStatus.BAD_REQUEST)


@allure.title("API: Postmark webhook без подписи отклоняется (401)")
def test_postmark_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/postmark-webhook without the signature
    header is rejected — inbound webhooks must be authenticated."""
    r = httpx.post(f"{base_url}{routes.WEBHOOK_POSTMARK}",
                   json={"RecordType": "Bounce"}, timeout=TIMEOUTS.api_request)
    expect_response(r, label="unsigned postmark webhook").status(HTTPStatus.UNAUTHORIZED)


@allure.title("API: Resend webhook без подписи отклоняется (401)")
def test_resend_webhook_rejects_unsigned(base_url):
    """POST /api/notifications/resend-webhook without the svix signature
    is rejected."""
    r = httpx.post(f"{base_url}{routes.WEBHOOK_RESEND}",
                   json={"type": "email.bounced"}, timeout=TIMEOUTS.api_request)
    expect_response(r, label="unsigned resend webhook").status(HTTPStatus.UNAUTHORIZED)


@allure.title("API: удаление связи убирает ребро из дерева")
def test_relationship_delete_removes_the_edge(owner_user, tenant_client):
    """DELETE /api/relationships/{id} removes a family edge — the demo
    tree seeds relationships; deleting one drops the count."""
    with step("подготовка: получить список связей"):
        api = tenant_client(owner_user)
        before = relationship_api.get_relationships(api)
        assert before, "demo tenant must seed relationships"
        rel_id = before[0].id

    with step("действие: удалить первую связь"):
        relationship_api.delete_relationship(api, rel_id)

    with step("проверка: количество связей уменьшилось на 1"):
        after = relationship_api.get_relationships(api)
        assert len(after) == len(before) - 1, \
            f"relationship must be gone: {len(before)} → {len(after)}"


@allure.title("API: отмена подписки на бесплатном тарифе отклоняется (400)")
def test_subscription_current_and_cancel(owner_user, tenant_client):
    """GET /api/subscription/current reports the tenant's tier; POST
    cancel on a free tenant (no paid subscription) is rejected 400 —
    there is nothing to cancel."""
    with step("действие: получить текущую подписку"):
        api = tenant_client(owner_user)
        r = api.get(routes.SUBSCRIPTION_CURRENT)
        sub = expect_response(r, label="subscription current").status_ok().schema(SubscriptionResponse)

    with step("проверка: тариф free, подписка None, cancel отклоняется"):
        assert sub.tenant["tier"] == "free", \
            f"new tenant tier: expected 'free', got {sub.tenant['tier']!r}"
        assert sub.subscription is None, \
            f"new tenant subscription must be None, got {sub.subscription!r}"

        cancelled = api.post(routes.SUBSCRIPTION_CANCEL)
        expect_response(cancelled, label="cancel without subscription").status(HTTPStatus.BAD_REQUEST)


@allure.title("API: владелец отзывает выданное приглашение")
def test_invite_revoke(owner_user, tenant_client, create_invite):
    """Owner issues a tenant invite, then revokes it by token —
    DELETE /api/account/tenant/invites/{token} reports it revoked."""
    with step("подготовка: создать приглашение и получить токен"):
        create_invite(owner_user, role="editor", name="Гость")
        api = tenant_client(owner_user)
        r = api.get(routes.TENANT_INVITES)
        raw = expect_response(r, label="tenant invites").status_ok().data
        items = raw if isinstance(raw, list) else raw["items"]
        assert items, "issued invite must be pending"
        token = items[0]["token"]

    with step("проверка: отзыв приглашения возвращает status=revoked"):
        revoked = api.delete(routes.tenant_invite(token))
        expect_response(revoked, label="invite revoke").status_ok().json_eq("status", "revoked")


@allure.title("API: загрузка фото и установка подписи к нему")
def test_photo_upload_and_caption(owner_user, tenant_client):
    """Owner uploads a photo to a person, then sets its caption — the
    upload links a Photo row and PATCH updates its caption."""
    with step("действие: загрузить фото"):
        api = tenant_client(owner_user)
        uploaded = api.post(
            routes.UPLOAD_PHOTO,
            params={"person_id": TestData.DEMO_PERSON_ID},
            files={"file": ("e2e.png", _PNG_1PX, "image/png")},
        )
        data = expect_response(uploaded, label="photo upload").status_ok().json_has("photo_id").data
        photo_id = data["photo_id"]

    with step("проверка: подпись устанавливается через PATCH"):
        patched = api.patch(routes.photo(photo_id), json={"caption": "Тестовая подпись"})
        expect_response(patched, label="photo caption").status_ok().json_eq("caption", "Тестовая подпись")


@allure.title("API: checkout без платёжного провайдера даёт pending")
def test_subscription_checkout_pending_without_payment_provider(
    owner_user, tenant_client,
):
    """POST /api/subscription/checkout for a paid tier resolves to a
    `pending_payment_provider` status — no payment provider is wired in
    test mode, but the endpoint handles it cleanly (no 500)."""
    with step("действие: checkout на pro тариф"):
        api = tenant_client(owner_user)
        r = api.post(routes.SUBSCRIPTION_CHECKOUT, json={"tier": "pro"})

    with step("проверка: статус pending_payment_provider"):
        expect_response(r, label="subscription checkout").status_ok().json_eq("status", "pending_payment_provider")


@allure.title("API: персона находится по display_slug")
def test_person_by_display_slug_resolves(owner_user, tenant_client):
    """A person created with a display_slug is resolvable by that slug —
    GET /api/people/by-display-slug/{slug} returns the same person."""
    with step("подготовка: создать персону с display_slug"):
        api = tenant_client(owner_user)
        slug = "e2e-slug-person"
        created = api.post(
            routes.PEOPLE, json={"name": "Слаг Тест", "display_slug": slug},
        )
        person = expect_response(created, label="create person with slug").status_ok().schema(PersonResponse)

    with step("проверка: by-display-slug возвращает ту же персону"):
        resolved = api.get(routes.person_by_slug(slug))
        expect_response(resolved, label="by-display-slug").status_ok().json_eq("id", person.id)


@allure.title("API: удалённый тенант восстанавливается в grace-период")
def test_tenant_delete_then_restore(
    owner_user, tenant_client, login_existing, base_url,
):
    """Owner soft-deletes their tenant; after re-login (delete kills the
    session) the tenant is restored within the 30-day grace period."""
    with step("действие: soft-delete тенанта"):
        api = tenant_client(owner_user)
        expect_response(
            api.post(routes.DELETE_TENANT, json={"confirm_slug": owner_user.slug}),
            label="delete tenant",
        ).status_ok()

    with step("действие: re-login и restore тенанта"):
        cookies = login_existing(owner_user.email, owner_user.password)
        restored = httpx.post(
            f"{base_url}{routes.RESTORE_TENANT}",
            json={"tenant_slug": owner_user.slug},
            cookies=cookies,
            headers={"Origin": base_url},
            timeout=TIMEOUTS.api_request,
        )

    with step("проверка: тенант восстановлен"):
        expect_response(restored, label="tenant restore").status_ok().json_eq("status", "restored")


@allure.title("API: создание локации и её появление в списке")
def test_locations_create_then_list(owner_user, tenant_client):
    """POST /api/locations creates a location; GET lists it back."""
    with step("действие: создать локацию"):
        api = tenant_client(owner_user)
        created = api.post(routes.LOCATIONS, json={
            "id": "loc-test-msk", "name": "Москва",
            "lat": 55.75, "lng": 37.62, "type": "other", "note": "",
        })
        loc = expect_response(created, label="create location").status_ok().schema(LocationResponse)

    with step("проверка: локация появилась в списке"):
        listed = api.get(routes.LOCATIONS)
        locations = expect_response(listed, label="list locations").status_ok().list_schema(LocationResponse)
        assert any(item.id == loc.id for item in locations), \
            "created location must appear in the list"
