"""SQL injection tests — payload в полях API инертен.

Инвариант (держится независимо от того, отклонил backend payload валидацией
или принял его): SQL-payload не выполняется — число строк БД не меняется,
демо-персона остаётся на месте, сервер не падает (не 5xx) и не отдаёт текст
SQL-ошибки. Проверка идёт против реального состояния БД, а не только по
статус-коду.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
import pytest

from api import routes
from assertions.base import should
from config.constants import TestConfig
from framework.step import step
from helpers.tree.tree_api import people
from src.texts import ErrMsg, TestData
from test_data.payloads.injection import SQL_PAYLOADS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в имени персоны инертен")
def test_person_name_sql_injection_is_inert(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], payload: str
) -> None:
    """SEC-INJ-5: SQL в name не выполняется — БД цела, не 5xx, без утечки SQL."""
    api = tenant_client(owner_user)

    with step("подготовка: запомнить состав персон до инъекции"):
        before = people(api)

    with step("действие: попытаться записать SQL-payload в имя демо-персоны"):
        r = api.patch(routes.person(TestData.DEMO_PERSON_ID), json={"name": payload})
        should.less(
            r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection
        )
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)

    with step("проверка: инъекция инертна — БД цела, демо-персона на месте"):
        after = people(api)
        should.have_length(after, len(before), ErrMsg.sql_injection_changed_row_count)
        demo = next((p for p in after if p["id"] == TestData.DEMO_PERSON_ID), None)
        should.not_none(demo, ErrMsg.demo_person_missing_after_injection)


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в email при signup отклоняется, сервер не падает")
def test_signup_email_sql_injection_rejected(base_url: str, payload: str) -> None:
    """SEC-INJ-6: SQL в signup email отклонён клиентской ошибкой (4xx), не 5xx, без утечки SQL."""
    with step("действие: signup с SQL-payload в email"):
        r = httpx.post(
            f"{base_url}{routes.SIGNUP}",
            json={
                "email": payload,
                "password": TestConfig.DEFAULT_PASSWORD,
                "full_name": "SQLi Test",
                "terms_accepted": True,
                "privacy_consent": True,
                "cross_border_consent": True,
            },
            headers={"Origin": base_url},
        )

    with step("проверка: невалидный email отклонён клиентской ошибкой, не 5xx"):
        should.greater_or_equal(r.status_code, HTTPStatus.BAD_REQUEST, ErrMsg.injection_status_unexpected)
        should.less(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection)
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)


@pytest.mark.security
@pytest.mark.parametrize("payload", SQL_PAYLOADS, ids=lambda p: p[:30])
@allure.title("SQL injection: payload в summary/notes инертен")
def test_person_patch_sql_injection_is_inert(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], payload: str
) -> None:
    """SEC-INJ-7: SQL в summary/notes не выполняется — БД цела, не 5xx."""
    api = tenant_client(owner_user)

    with step("подготовка: запомнить состав персон до инъекции"):
        before = people(api)

    with step("действие: попытаться записать SQL-payload в summary и notes демо-персоны"):
        r = api.patch(
            routes.person(TestData.DEMO_PERSON_ID), json={"summary": payload, "notes": payload}
        )
        should.less(
            r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.server_error_on_injection
        )
        should.not_contain(r.text.lower(), "syntax error", ErrMsg.sql_error_leaked_in_body)

    with step("проверка: БД цела после инъекции в summary/notes"):
        after = people(api)
        should.have_length(after, len(before), ErrMsg.sql_injection_changed_row_count)
        demo = next((p for p in after if p["id"] == TestData.DEMO_PERSON_ID), None)
        should.not_none(demo, ErrMsg.demo_person_missing_after_injection)
