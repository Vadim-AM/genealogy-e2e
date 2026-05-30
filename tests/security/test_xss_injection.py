"""XSS injection tests — payload в полях персоны/сайта не исполняется в DOM.

Инвариант (держится независимо от механизма защиты): какой бы XSS-вектор ни
попытались записать, в браузере не должно произойти исполнения скрипта —
никаких alert/confirm/prompt. Backend защищается одним из двух способов:
отклоняет payload валидацией (4xx) ИЛИ принимает и экранирует при рендере;
оба исхода безопасны, 5xx или реальный JS-диалог — провал. Детектор диалогов
(`watch_dialogs`) ловит фактическое исполнение для любого payload.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import pytest

from api import routes, site_api
from assertions.base import should
from framework.step import step
from helpers.tree.tree_api import people_count
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData
from test_data.payloads.injection import XSS_PAYLOADS

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в имени персоны не исполняется в дереве")
def test_person_name_xss_does_not_execute(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-1: XSS-payload в name персоны не исполняется в браузере."""
    api = tenant_client(owner_user)

    with step("подготовка: запомнить число персон и повесить детектор диалогов"):
        count_before = people_count(api)
        tree = pages.create(TreePage)
        dialogs = tree.watch_dialogs()

    with step("действие: попытаться записать XSS-payload в имя демо-персоны"):
        r = api.patch(routes.person(TestData.DEMO_PERSON_ID), json={"name": payload})
        should.less(
            r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection
        )

    with step("проверка: дерево не исполняет payload, БД цела"):
        tree.goto()
        tree.expect_tree_rendered()
        should.be_empty(dialogs, ErrMsg.xss_executed)
        should.be_equal(people_count(api), count_before, ErrMsg.sql_injection_changed_row_count)


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в summary персоны не исполняется в профиле")
def test_person_summary_xss_does_not_execute(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-2: XSS-payload в summary персоны не исполняется в браузере."""
    api = tenant_client(owner_user)

    with step("подготовка: повесить детектор JS-диалогов на страницу"):
        tree = pages.create(TreePage)
        dialogs = tree.watch_dialogs()

    with step("действие: попытаться записать XSS-payload в summary демо-персоны"):
        r = api.patch(routes.person(TestData.DEMO_PERSON_ID), json={"summary": payload})
        should.less(
            r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection
        )

    with step("проверка: профиль не исполняет payload"):
        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        should.be_empty(dialogs, ErrMsg.xss_executed)


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в названии сайта не исполняется на главной")
def test_site_name_xss_does_not_execute(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-3: XSS в site_name принимается и экранируется — не исполняется на главной."""
    api = tenant_client(owner_user)

    with step("подготовка: повесить детектор JS-диалогов на страницу"):
        tree = pages.create(TreePage)
        dialogs = tree.watch_dialogs()

    with step("действие: записать XSS-payload в site_name"):
        site_api.patch_site_config(api, site_name=payload)

    with step("проверка: главная рендерит payload как текст, без исполнения"):
        tree.goto()
        tree.expect_tree_rendered()
        should.be_empty(dialogs, ErrMsg.xss_executed)
