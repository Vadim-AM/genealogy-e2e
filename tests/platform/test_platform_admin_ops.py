"""Backend invariants for superadmin platform/admin endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import httpx
import pyotp

from api import mfa_api, routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


@allure.title("Админ: суперадмин видит список тенантов и свой в нём")
def test_admin_tenant_listing(superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]) -> None:
    """Superadmin lists all tenants and looks one up by slug."""
    with step("действие: получаем список тенантов"):
        api = tenant_client(superadmin_user)
        r = api.get(routes.ADMIN_TENANTS)
        raw = expect_response(r, label="GET admin/tenants").status_ok().data
        tenants = raw if isinstance(raw, list) else raw["items"]

    with step("проверка: собственный тенант в списке"):
        should.any_match(tenants, lambda t_item: t_item["slug"] == superadmin_user.slug, ErrMsg.own_tenant_missing)

    with step("проверка: GET тенанта по slug возвращает правильный slug"):
        one = api.get(routes.admin_tenant(superadmin_user.slug))
        expect_response(one, label="GET admin/tenant by slug").status_ok().json_eq("slug", superadmin_user.slug)


@allure.title("Вейтлист: подписка, пометка и удаление через админку")
def test_admin_waitlist_lifecycle(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], base_url: str
) -> None:
    """A waitlist subscriber appears for superadmin, can be marked."""
    with step("подготовка: подписываем email на вейтлист"):
        email = unique_email("wl-admin")
        expect_response(
            httpx.post(
                f"{base_url}{routes.WAITLIST_SUBSCRIBE}",
                json={"email": email},
            ),
            label="waitlist subscribe",
        ).status_ok()

    with step("проверка: подписчик виден в admin waitlist"):
        api = tenant_client(superadmin_user)
        r = api.get(routes.ADMIN_WAITLIST)
        items = expect_response(r, label="GET admin/waitlist").status_ok().data
        sub = should.not_none(
            next((s for s in items if s["email"] == email), None), ErrMsg.item_not_found
        )

    with step("действие: помечаем contacted и удаляем подписчика"):
        expect_response(
            api.patch(routes.admin_waitlist_item(sub["id"]), json={"contacted": True}),
            label="PATCH waitlist item contacted",
        ).status_ok()
        expect_response(
            api.delete(routes.admin_waitlist_item(sub["id"])),
            label="DELETE waitlist item",
        ).status_ok()

    with step("проверка: удалённый подписчик больше не в списке"):
        r2 = api.get(routes.ADMIN_WAITLIST)
        after = expect_response(r2, label="GET admin/waitlist after").status_ok().data
        should.be_false(any(s["id"] == sub["id"] for s in after), ErrMsg.item_not_found)


@allure.title("Вейтлист платформы: подписчик виден суперадмину")
def test_platform_waitlist_listing(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], base_url: str
) -> None:
    """GET /api/platform/waitlist lists waitlist subscribers for the."""
    with step("подготовка: подписываем email на вейтлист"):
        email = unique_email("plat-wl")
        expect_response(
            httpx.post(
                f"{base_url}{routes.WAITLIST_SUBSCRIBE}",
                json={"email": email},
            ),
            label="waitlist subscribe",
        ).status_ok()

    with step("проверка: подписчик виден в platform waitlist"):
        api = tenant_client(superadmin_user)
        r = api.get(routes.PLATFORM_WAITLIST)
        raw = expect_response(r, label="GET platform/waitlist").status_ok().data
        items = raw if isinstance(raw, list) else raw["items"]
        should.any_match(items, lambda s: s.get("email") == email, ErrMsg.item_not_found)


@allure.title("Бэкапы и напоминания: список снимков и отправка нуджей")
def test_platform_backups_and_nudges(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """GET /api/platform/backups lists snapshots; POST send-onboarding-nudges."""
    with step("действие: получаем список бэкапов"):
        api = tenant_client(superadmin_user)
        backups = api.get(routes.PLATFORM_BACKUPS)
        expect_response(backups, label="GET backups").status_ok().json_has("items")

    with step("действие: отправляем onboarding nudges"):
        nudges = api.post(routes.PLATFORM_NUDGES)
        expect_response(nudges, label="POST nudges").status_ok().json_has("sent_count")


@allure.title("Оверрайд тенанта: установка, чтение и удаление переопределения")
def test_tenant_override_lifecycle(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Superadmin sets a tier override on a tenant, reads it back, deletes."""
    with step("подготовка: настраиваем MFA и step-up"):
        api = tenant_client(superadmin_user)
        setup = mfa_api.setup_mfa(api)
        totp = pyotp.TOTP(setup.secret)
        mfa_api.verify_mfa(api, totp.now())
        expect_response(
            api.post(routes.MFA_STEP_UP, json={"method": "totp", "code": totp.now()}),
            label="MFA step-up",
        ).status_ok()

    with step("действие: создаём override max_archives=999"):
        slug = superadmin_user.slug
        expect_response(
            api.post(
                routes.PLATFORM_TENANT_OVERRIDE,
                json={
                    "tenant_slug": slug,
                    "field_name": "max_archives",
                    "value": "999",
                },
            ),
            label="POST tenant override",
        ).status_ok()

    with step("проверка: override виден в списке"):
        r = api.get(routes.tenant_overrides(slug))
        overrides_data = expect_response(r, label="GET tenant overrides").status_ok().data
        should.any_match(overrides_data["items"], lambda o: o["field_name"] == "max_archives", ErrMsg.item_not_found)

    with step("действие: удаляем override и проверяем"):
        expect_response(
            api.delete(routes.tenant_override_field(slug, "max_archives")),
            label="DELETE tenant override",
        ).status_ok()
        r2 = api.get(routes.tenant_overrides(slug))
        after = expect_response(r2, label="GET tenant overrides after").status_ok().data
        should.be_false(any(o["field_name"] == "max_archives" for o in after["items"]), ErrMsg.item_not_found)


@allure.title("Вейтлист: инвайт подписчика возвращает статус invited")
def test_platform_waitlist_invite_promotes_subscriber(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], base_url: str
) -> None:
    """POST /api/platform/waitlist/{id}/invite promotes a waitlist."""
    with step("подготовка: подписываем email на вейтлист"):
        email = unique_email("wl-invite")
        expect_response(
            httpx.post(
                f"{base_url}{routes.WAITLIST_SUBSCRIBE}",
                json={"email": email},
            ),
            label="waitlist subscribe",
        ).status_ok()

    with step("подготовка: находим подписчика в admin waitlist"):
        api = tenant_client(superadmin_user)
        r = api.get(routes.ADMIN_WAITLIST)
        items = expect_response(r, label="GET admin/waitlist").status_ok().data
        sub = next(s for s in items if s["email"] == email)

    with step("действие: инвайтим подписчика"):
        invited = api.post(routes.platform_waitlist_invite(sub["id"]))

    with step("проверка: статус invited или already_exists"):
        inv_data = expect_response(invited, label="waitlist invite").status_ok().data
        should.be_in(inv_data["status"], ("invited", "already_exists"), ErrMsg.subscribe_status_wrong)
