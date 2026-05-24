"""SQL injection tests — payloads in API fields must not cause 500 or data leaks.

SEC-INJ-5..7: SQL vectors in person fields, search, and signup email
must be rejected with 4xx (validation) or safely stored as text, never
triggering a backend 500 or raw SQL error in the response body.
"""

from __future__ import annotations

from uuid import uuid4

import allure
import httpx
import pytest

from tests._data.payloads.injection import SQL_PAYLOADS
from tests.api_paths import API
from tests.step import step


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в имени персоны не вызывает 500")
def test_person_name_sql_injection_safe(
    owner_user,
    tenant_client,
    payload,
):
    """SEC-INJ-5: SQL в person name → 2xx (stored as text) or 4xx, never 500."""
    api = tenant_client(owner_user)
    pid = f"sqli-{uuid4().hex[:8]}"

    with step("создать персону с SQL-payload в имени"):
        r = api.post(API.PEOPLE, json={
            "id": pid,
            "name": payload,
            "branch": "paternal",
            "gender": "m",
        })

    with step("проверить что backend не упал"):
        assert r.status_code < 500, (
            f"SQL injection caused server error {r.status_code}: {r.text[:300]}"
        )
        assert "syntax error" not in r.text.lower(), (
            f"Raw SQL error leaked in response: {r.text[:300]}"
        )
        assert "pg_tables" not in r.text.lower(), (
            f"Internal table names leaked: {r.text[:300]}"
        )


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в email при signup не вызывает 500")
def test_signup_email_sql_injection_safe(
    base_url,
    payload,
):
    """SEC-INJ-6: SQL in signup email → 422 (validation), never 500."""
    with step("отправить signup с SQL-payload в email"):
        r = httpx.post(
            f"{base_url}{API.SIGNUP}",
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
        assert r.status_code < 500, (
            f"SQL injection in email caused server error {r.status_code}: {r.text[:300]}"
        )
        assert "syntax error" not in r.text.lower(), (
            f"Raw SQL error leaked: {r.text[:300]}"
        )


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в PATCH person fields не вызывает 500")
def test_person_patch_sql_injection_safe(
    owner_user,
    tenant_client,
    payload,
):
    """SEC-INJ-7: SQL in PATCH person summary/notes → safe."""
    api = tenant_client(owner_user)

    with step("обновить summary демо-персоны с SQL-payload"):
        from tests.messages import TestData

        r = api.patch(API.person(TestData.DEMO_PERSON_ID), json={
            "summary": payload,
            "notes": payload,
        })

    with step("проверить что backend не упал и не утёк SQL"):
        assert r.status_code < 500, (
            f"SQL injection caused server error {r.status_code}: {r.text[:300]}"
        )
        assert "syntax error" not in r.text.lower(), (
            f"Raw SQL error leaked in response: {r.text[:300]}"
        )
