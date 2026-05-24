"""Role-based access — INV-PERM-003a (viewer read).

После accept invite с role=viewer пользователь должен иметь
**read-only** access к древу и профилям. Run security 28.04 night
выявил, что viewer'ы получали 403 на GET endpoints — endpoint'ы
требовали `require_editor` вместо `require_viewer`.

Closed by upstream commit `fded6c7`. Regression-trail для контракта.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from tests._core.api_paths import API
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step


@allure.title("Роли: viewer может читать дерево владельца")
def test_viewer_can_read_tree(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data.

    Was xfail until upstream commit `fded6c7`. Regression-trail.
    """
    with step("действие: viewer запрашивает дерево"):
        _, viewer = viewer_in_owners_tenant
        r = tenant_client(viewer).get(API.TREE)

    with step("проверка: 200 OK"):
        expect_response(r, label="viewer GET tree").status(HTTPStatus.OK)


@allure.title("Роли: viewer может читать профиль персоны")
def test_viewer_can_read_person(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(API.person(TestData.DEMO_PERSON_ID))
    expect_response(r, label="viewer GET person").status(HTTPStatus.OK)
