"""SQL injection tests — payloads in API fields must not cause 500 or data leaks."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

import allure
import httpx
import pytest

from api import routes
from assertions.base import should
from framework.step import step
from src.texts import ErrMsg, TestData
from test_data.payloads.injection import SQL_PAYLOADS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в имени персоны не вызывает 500")
def test_person_name_sql_injection_safe(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], payload: str
) -> None:
    """SEC-INJ-5: SQL в person name → 2xx (stored as text) or 4xx, never 500."""
    api = tenant_client(owner_user)
    pid = f"sqli-{uuid4().hex[:8]}"

    with step("создать персону с SQL-payload в имени"):
        r = api.post(
            routes.PEOPLE,
            json={
                "id": pid,
                "name": payload,
                "branch": "paternal",
                "gender": "m",
            },
        )

    with step("проверить что backend не упал"):
        should.less(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection)
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)
        should.not_contain(r.text.lower(), "pg_tables", ErrMsg.internal_tables_leaked)


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в email при signup не вызывает 500")
def test_signup_email_sql_injection_safe(base_url: str, payload: str) -> None:
    """SEC-INJ-6: SQL in signup email → 422 (validation), never 500."""
    with step("отправить signup с SQL-payload в email"):
        r = httpx.post(
            f"{base_url}{routes.SIGNUP}",
            json={
                "email": payload,
                "password": "test_password_8plus",
                "full_name": "SQLi Test",
                "terms_accepted": True,
                "privacy_consent": True,
                "cross_border_consent": True,
            },
            headers={"Origin": base_url},
        )

    with step("проверить что backend вернул 4xx, не 500"):
        should.less(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection)
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в PATCH person fields не вызывает 500")
def test_person_patch_sql_injection_safe(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], payload: str
) -> None:
    """SEC-INJ-7: SQL in PATCH person summary/notes → safe."""
    api = tenant_client(owner_user)

    with step("обновить summary демо-персоны с SQL-payload"):
        r = api.patch(
            routes.person(TestData.DEMO_PERSON_ID),
            json={
                "summary": payload,
                "notes": payload,
            },
        )

    with step("проверить что backend не упал и не утёк SQL"):
        should.less(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection)
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)
