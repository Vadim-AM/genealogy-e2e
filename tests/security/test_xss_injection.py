"""XSS injection tests — payloads in person fields must not execute in DOM.

Backend may either: (a) accept the payload (201) and rely on frontend escaping,
or (b) reject it at validation (422) — both are safe. The test passes in either case.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

import allure
import pytest

from api import routes, site_api
from assertions.base import should
from framework.step import step
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
@allure.title("XSS: payload в имени персоны не исполняется")
def test_person_name_xss_is_escaped(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-1: XSS в поле name — backend отклоняет (422) или frontend экранирует."""
    api = tenant_client(owner_user)
    pid = f"xss-{uuid4().hex[:8]}"

    with step("создать персону с XSS-payload в имени"):
        r = api.post(
            routes.PEOPLE,
            json={"id": pid, "name": payload, "branch": "paternal", "gender": "m"},
        )

    if r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        return

    with step("открыть дерево и проверить экранирование"):
        should.be_equal(r.status_code, HTTPStatus.CREATED, ErrMsg.response_not_ok)
        _ = pages.navigate_to(TreePage)
        content = owner_page.content()
        should.not_contain(content, "<script>alert", ErrMsg.xss_script_rendered)
        should.not_contain(content, "onerror=alert", ErrMsg.xss_handler_rendered)
        should.not_contain(content, "onload=alert", ErrMsg.xss_handler_rendered)


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в summary/notes персоны не исполняется")
def test_person_notes_xss_is_escaped(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-2: XSS в поле summary — backend отклоняет или frontend экранирует."""
    api = tenant_client(owner_user)

    with step("обновить summary демо-персоны с XSS-payload"):
        r = api.patch(routes.person(TestData.DEMO_PERSON_ID), json={"summary": payload})

    if r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        return

    with step("открыть профиль и проверить экранирование"):
        should.be_true(r.is_success, ErrMsg.response_not_ok)
        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        content = owner_page.content()
        should.not_contain(content, "<script>alert", ErrMsg.xss_script_rendered)
        should.not_contain(content, "onerror=alert", ErrMsg.xss_handler_rendered)


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в названии сайта экранируется")
def test_site_name_xss_is_escaped(
    owner_page: Page,
    owner_user: AuthUser,
    tenant_client: Callable[[AuthUser], httpx.Client],
    payload: str,
    pages: PageFactory,
) -> None:
    """SEC-INJ-3: XSS в site_name не исполняется на главной."""
    api = tenant_client(owner_user)

    with step("установить site_name с XSS-payload"):
        site_api.patch_site_config(api, site_name=payload)

    with step("открыть главную и проверить экранирование"):
        _ = pages.navigate_to(TreePage)
        content = owner_page.content()
        should.not_contain(content, "<script>alert", ErrMsg.xss_script_rendered)
        should.not_contain(content, "onerror=alert", ErrMsg.xss_handler_rendered)
