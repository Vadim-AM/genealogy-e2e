"""Platform superadmin dashboard — TC-PA-* metrics, tenants table, free-license-grant."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.platform_dashboard_page import PlatformDashboardPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import BrowserContext, Expect

    from fixtures.users import AuthUser


@allure.title("Дашборд платформы: страница открывается для суперадмина")
def test_platform_dashboard_loads_for_superadmin(
    auth_context_factory: Callable[..., BrowserContext], superadmin_user: AuthUser
) -> None:
    """TC-PA-1: superadmin can open /platform/dashboard."""
    with step("подготовка: создаём контекст суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()

    with step("проверка: дашборд отвечает 200"):
        response = page.goto("/platform/dashboard")
        should.not_none(response, ErrMsg.platform_navigation_failed)
        should.be_equal(response.status, HTTPStatus.OK, ErrMsg.status_mismatch)


@allure.title("Дашборд платформы: карточки метрик отображаются")
def test_platform_metrics_visible(
    auth_context_factory: Callable[..., BrowserContext], superadmin_user: AuthUser, soft_check: Expect
) -> None:
    """TC-PA-2: metrics cards rendered."""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        dashboard = PlatformDashboardPage(page)
        dashboard.goto_and_load()

    with step("проверка: карточки метрик отображаются"):
        dashboard.soft_check_metrics_loaded(soft_check)


@allure.title("Метрики платформы: обычный владелец получает 403")
def test_platform_metrics_endpoint_403_for_non_super(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-3: regular owner gets 401 or 403 on /api/platform/metrics."""
    r = tenant_client(owner_user).get(routes.PLATFORM_METRICS)
    expect_response(
        r,
        label="non-superadmin reached platform metrics",
    ).status(HTTPStatus.FORBIDDEN)


@allure.title("Метрики платформы: ответ содержит tenants_active и signups_total")
def test_platform_metrics_endpoint_200_for_super(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-PA-4: superadmin gets 200 on /api/platform/metrics with the canonical."""
    with step("действие: запрашиваем метрики платформы"):
        r = tenant_client(superadmin_user).get(routes.PLATFORM_METRICS)
        data = expect_response(r, label="platform metrics").status_ok().data

    with step("проверка: tenants_active и signups_total — целые числа"):
        for key in ("tenants_active", "signups_total"):
            should.be_in(key, data, ErrMsg.metric_key_missing)
            should.be_instance(data[key], int, ErrMsg.metric_type_wrong)
