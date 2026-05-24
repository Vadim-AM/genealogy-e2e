"""XSS injection tests — payloads in person fields must be escaped in HTML.

SEC-INJ-1..4: XSS vectors in person name, site name, search, and notes
are stored by the backend but MUST be HTML-escaped when rendered in the
browser. A passing test = the raw payload appears as text, not as active
DOM elements.
"""

from __future__ import annotations

from uuid import uuid4

import allure
import pytest

from tests._data.payloads.injection import XSS_PAYLOADS
from tests.api_paths import API
from tests.response import expect_response
from tests.step import step


@pytest.mark.security
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=lambda p: p[:30])
@allure.title("XSS: payload в имени персоны экранируется при рендере")
def test_person_name_xss_is_escaped(
    owner_page,
    owner_user,
    tenant_client,
    payload,
):
    """SEC-INJ-1: XSS в поле name персоны не исполняется в DOM."""
    api = tenant_client(owner_user)
    pid = f"xss-{uuid4().hex[:8]}"

    with step("создать персону с XSS-payload в имени"):
        r = api.post(API.PEOPLE, json={
            "id": pid,
            "name": payload,
            "branch": "paternal",
            "gender": "m",
        })
        expect_response(r).status_ok()

    with step("открыть дерево и проверить экранирование"):
        owner_page.goto("/")
        owner_page.wait_for_load_state("domcontentloaded")
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
):
    """SEC-INJ-2: XSS в поле summary не исполняется при просмотре профиля."""
    api = tenant_client(owner_user)

    with step("обновить summary демо-персоны с XSS-payload"):
        from tests.messages import TestData

        r = api.patch(API.person(TestData.DEMO_PERSON_ID), json={"summary": payload})
        expect_response(r).status_ok()

    with step("открыть профиль и проверить экранирование"):
        owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
        owner_page.wait_for_load_state("domcontentloaded")
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
):
    """SEC-INJ-3: XSS в site_name не исполняется на главной."""
    api = tenant_client(owner_user)

    with step("установить site_name с XSS-payload"):
        r = api.patch(API.SITE_CONFIG, json={"site_name": payload})
        expect_response(r).status_ok()

    with step("открыть главную и проверить экранирование"):
        owner_page.goto("/")
        owner_page.wait_for_load_state("domcontentloaded")
        content = owner_page.content()
        assert "<script>alert" not in content, f"XSS payload in site_name rendered as HTML: {payload}"
        assert "onerror=alert" not in content, f"XSS event handler in site_name: {payload}"
