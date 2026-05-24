"""Role-based access — INV-PERM-003a (viewer read)."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes
from framework.response import expect_response
from framework.step import step
from src.texts import TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Роли: viewer может читать дерево владельца")
def test_viewer_can_read_tree(
    viewer_in_owners_tenant: tuple[AuthUser, AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data."""
    with step("действие: viewer запрашивает дерево"):
        _, viewer = viewer_in_owners_tenant
        r = tenant_client(viewer).get(routes.TREE)

    with step("проверка: 200 OK"):
        expect_response(r, label="viewer GET tree").status(HTTPStatus.OK)


@allure.title("Роли: viewer может читать профиль персоны")
def test_viewer_can_read_person(
    viewer_in_owners_tenant: tuple[AuthUser, AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(routes.person(TestData.DEMO_PERSON_ID))
    expect_response(r, label="viewer GET person").status(HTTPStatus.OK)
