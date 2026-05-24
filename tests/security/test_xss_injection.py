"""XSS injection tests — payloads in person fields must be escaped in HTML.

SEC-INJ-1..4: XSS vectors in person name, site name, search, and notes
are stored by the backend but MUST be HTML-escaped when rendered in the
browser. A passing test = the raw payload appears as text, not as active
DOM elements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import allure
import pytest

from api import person_api, site_api
from framework.step import step
from models.person import PersonCreate
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import TestData
from test_data.payloads.injection import XSS_PAYLOADS

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в имени персоны экранируется при рендере")
def test_person_name_xss_is_escaped(
    owner_page,
    owner_user,
    tenant_client,
    payload,
    pages: PageFactory,
):
    """SEC-INJ-1: XSS в поле name персоны не исполняется в DOM."""
    api = tenant_client(owner_user)
    pid = f"xss-{uuid4().hex[:8]}"

    with step("создать персону с XSS-payload в имени"):
        person_api.create_person(api, PersonCreate(
            id=pid,
            name=payload,
            branch="paternal",
            gender="m",
        ))

    with step("открыть дерево и проверить экранирование"):
        _ = pages.navigate_to(TreePage)
        content = owner_page.content()
        assert "<script>alert" not in content, f"XSS payload rendered as executable HTML: {payload}"
        assert "onerror=alert" not in content, f"XSS event handler rendered: {payload}"
        assert "onload=alert" not in content, f"XSS event handler rendered: {payload}"


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в summary/notes персоны экранируется")
def test_person_notes_xss_is_escaped(
    owner_page,
    owner_user,
    tenant_client,
    payload,
    pages: PageFactory,
):
    """SEC-INJ-2: XSS в поле summary не исполняется при просмотре профиля."""
    api = tenant_client(owner_user)

    with step("обновить summary демо-персоны с XSS-payload"):
        person_api.patch_person(api, TestData.DEMO_PERSON_ID, summary=payload)

    with step("открыть профиль и проверить экранирование"):
        ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        content = owner_page.content()
        assert "<script>alert" not in content, f"XSS payload in summary rendered as HTML: {payload}"
        assert "onerror=alert" not in content, f"XSS event handler in summary: {payload}"


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в названии сайта экранируется")
def test_site_name_xss_is_escaped(
    owner_page,
    owner_user,
    tenant_client,
    payload,
    pages: PageFactory,
):
    """SEC-INJ-3: XSS в site_name не исполняется на главной."""
    api = tenant_client(owner_user)

    with step("установить site_name с XSS-payload"):
        site_api.patch_site_config(api, site_name=payload)

    with step("открыть главную и проверить экранирование"):
        _ = pages.navigate_to(TreePage)
        content = owner_page.content()
        assert "<script>alert" not in content, f"XSS payload in site_name rendered as HTML: {payload}"
        assert "onerror=alert" not in content, f"XSS event handler in site_name: {payload}"
