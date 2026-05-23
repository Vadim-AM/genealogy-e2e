"""Role-based access — INV-PERM-003a (viewer read).

После accept invite с role=viewer пользователь должен иметь
**read-only** access к древу и профилям. Run security 28.04 night
выявил, что viewer'ы получали 403 на GET endpoints — endpoint'ы
требовали `require_editor` вместо `require_viewer`.

Closed by upstream commit `fded6c7`. Regression-trail для контракта.
"""

from __future__ import annotations

import allure

from tests.api_paths import API
from tests.messages import TestData
from tests.response import expect_response


@allure.title("Роли: viewer может читать дерево (GET /api/tree)")
def test_viewer_can_read_tree(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data.

    Was xfail until upstream commit `fded6c7`. Regression-trail.
    """
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(API.TREE)
    expect_response(r, label="viewer GET tree").status(200)


@allure.title("Роли: viewer может читать профиль персоны")
def test_viewer_can_read_person(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(API.person(TestData.DEMO_PERSON_ID))
    expect_response(r, label="viewer GET person").status(200)
