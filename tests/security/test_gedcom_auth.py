"""INV-GEDCOM-001: GEDCOM endpoints not migrated to auth_v2."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser
from assertions.base import should
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg


@allure.title("GEDCOM: владелец экспортирует дерево через auth_v2")
def test_owner_can_export_gedcom_via_auth_v2(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """INV-GEDCOM-001 (export): auth_v2 owner получает 200 + GEDCOM body."""
    with step("действие: экспортировать GEDCOM через auth_v2"):
        api = tenant_client(owner_user)
        r = api.get(routes.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)

    with step("проверка: 200 и тело начинается с '0 HEAD'"):
        expect_response(r, label="GEDCOM export auth_v2").status(HTTPStatus.OK)
        # GEDCOM-формат начинается с '0 HEAD'. Response charset=utf-8
        # (см. test_owner_ui::test_owner_export_gedcom_returns_valid_dump),
        # так что r.text — корректно декодированная строка.
        should.contain(r.text[:200], "0 HEAD", ErrMsg.gedcom_header_missing)


@allure.title("GEDCOM: владелец импортирует файл через auth_v2")
def test_owner_can_import_gedcom_via_auth_v2(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """INV-GEDCOM-001 (import): auth_v2 owner может POST GEDCOM."""
    with step("подготовка: подготовить минимальный GEDCOM-файл"):
        api = tenant_client(owner_user)
        minimal_gedcom = "0 HEAD\n1 SOUR Genealogy-e2e\n0 @I1@ INDI\n1 NAME Тестовый /Импорт/\n0 TRLR\n"

    with step("действие: импортировать GEDCOM через auth_v2"):
        r = api.post(
            routes.ADMIN_IMPORT_GEDCOM,
            files={"file": ("import.ged", minimal_gedcom.encode("utf-8"), "application/octet-stream")},
            timeout=TIMEOUTS.api_long,
        )

    with step("проверка: импорт принят (200)"):
        expect_response(r, label="GEDCOM import auth_v2").status(HTTPStatus.OK)
