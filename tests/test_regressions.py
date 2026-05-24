"""Regression suite for closed BUG-* tickets per docs/test-plan.md."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import person_api, routes, site_api
from assertions.base import should
from config.constants import unique_email
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from pages.signup_page import SignupPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser


@allure.title("Регрессия: auth_v2 владелец читает историю обогащения")
def test_bug_auth_001_authv2_owner_reads_enrichment(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """TC-BUG-AUTH-001: auth_v2 owner can hit GET /api/enrich/{id}/history without 401."""
    with step("подготовка: consent и получение pid"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        should.not_empty(tree.people, ErrMsg.demo_people_missing)
        pid = tree.people[0].id

    with step("проверка: history и acceptances доступны (200/204)"):
        for path in (routes.enrich_history(pid), routes.enrich_acceptances(pid)):
            r = api.get(path)
            expect_response(r, label=f"GET {path}").status(HTTPStatus.OK, HTTPStatus.NO_CONTENT)


@allure.title("Регрессия: аналитика page_view не падает с 500")
def test_bug_auth_002_pageview_platform_session_no_500(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-BUG-AUTH-002: /api/analytics/log with PlatformSession cookie returns 204."""
    with step("действие: отправка page_view аналитики"):
        api = tenant_client(owner_user)
        r = api.post(
            routes.ANALYTICS_LOG,
            json={"event": "page_view", "path": "/", "context": {"section": "tree"}},
        )

    with step("проверка: endpoint вернул 200"):
        expect_response(r, label="BUG-AUTH-002 analytics log").status(HTTPStatus.OK)


@allure.title("Регрессия: /signup не запрашивает /api/csrf-token (404)")
def test_bug_csrf_001_console_clean_on_signup(page: Page, anon_pages: PageFactory) -> None:
    """TC-BUG-CSRF-001: opening /signup → no 404 on /api/csrf-token in console."""
    with step("действие: открыть /signup и слушать 404 на /api/csrf-token"):
        bad_404: list[str] = []
        page.on(
            "response",
            lambda r: (
                bad_404.append(r.url)
                if r.status == HTTPStatus.NOT_FOUND and "/api/csrf-token" in r.url  # noqa: drift
                else None
            ),
        )
        _ = anon_pages.navigate_to(SignupPage)

    with step("проверка: нет 404 на /api/csrf-token"):
        should.be_empty(bad_404, ErrMsg.js_errors_on_page)


@allure.title("Регрессия: site_config изолирован между тенантами")
def test_bug_mt_001_site_config_is_per_tenant(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """BUG-MT-001 regression: PATCH /api/site/config in tenant A must NOT affect tenant B."""
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api(email=unique_email("config-a"))
        user_b = signup_via_api(email=unique_email("config-b"))
        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: изменить site_name в тенанте A"):
        site_api.patch_site_config(api_a, site_name="Tenant A Brand")

    with step("проверка: тенант B не содержит site_name тенанта A"):
        config_b = site_api.get_site_config(api_b)
        should.not_equal(config_b.site_name, "Tenant A Brand", ErrMsg.config_leaked)


@allure.title("Регрессия: повторный запрос обогащения не даёт 409")
def test_bug_auth_003_sse_reconnect_recovers(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """TC-BUG-AUTH-003 regression: re-issuing a streaming enrichment for the."""
    with step("подготовка: consent и получение pid"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        tree = person_api.get_tree(api)
        should.not_empty(tree.people, ErrMsg.demo_people_missing)
        pid = tree.people[0].id

    with step("действие: первый streaming enrichment POST"):
        r1 = api.post(
            routes.enrich(pid),
            json={"streaming": True, "force_refresh": False},
            timeout=TIMEOUTS.api_long,
        )
        expect_response(r1, label="first enrich POST").status(HTTPStatus.OK)

    with step("проверка: повторный POST возвращает 200, не 409"):
        r2 = api.post(
            routes.enrich(pid),
            json={"streaming": True, "force_refresh": False},
            timeout=TIMEOUTS.api_long,
        )
        expect_response(r2, label="BUG-AUTH-003 reconnect").status(HTTPStatus.OK)
