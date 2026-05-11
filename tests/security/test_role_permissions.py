"""Role-based access — INV-PERM-003a (viewer read).

После accept invite с role=viewer пользователь должен иметь
**read-only** access к древу и профилям. Run security 28.04 night
выявил, что viewer'ы получали 403 на GET endpoints — endpoint'ы
требовали `require_editor` вместо `require_viewer`.

Closed by upstream commit `fded6c7`. Regression-trail для контракта.
"""

from __future__ import annotations

import httpx
import pytest

from tests._fixtures.users import AuthUser
from tests.api_paths import API
from tests.constants import TestConfig, unique_email
from tests.messages import TestData
from tests.timeouts import TIMEOUTS


@pytest.fixture
def viewer_in_owners_tenant(
    signup_via_api, signup_unverified, read_email_token, login_existing,
    create_invite, accept_invite, base_url: str,
):
    """Build a viewer-membership pair: returns (owner, viewer_auth_user).

    `viewer_auth_user` is an `AuthUser` whose `slug` points at the **owner's**
    tenant (cross-tenant access via membership) so `tenant_client(viewer)`
    routes requests to the right tenant.
    """
    owner = signup_via_api(email=unique_email("owner"))
    viewer_email = unique_email("viewer")

    # Secondary user: signup → verify (token в body — commit d860de8) → login.
    signup_unverified(email=viewer_email)
    verify_token = read_email_token(viewer_email)
    httpx.post(
        f"{base_url}{API.VERIFY_EMAIL}",
        json={"token": verify_token},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    viewer_cookies = login_existing(viewer_email)

    # Owner creates invite, secondary user accepts.
    invite_token = create_invite(owner, role="viewer", name="Тётя")
    accept_invite(invite_token, cookies=viewer_cookies)

    viewer = AuthUser(
        email=viewer_email,
        password=TestConfig.DEFAULT_PASSWORD,
        slug=owner.slug,
        cookies=viewer_cookies,
    )
    return owner, viewer


def test_viewer_can_read_tree(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data.

    Was xfail until upstream commit `fded6c7`. Regression-trail.
    """
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(API.TREE)
    assert r.status_code == 200, (
        f"viewer GET {API.TREE} should be 200, got {r.status_code}: {r.text[:200]}"
    )


def test_viewer_can_read_person(viewer_in_owners_tenant, tenant_client):
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    _, viewer = viewer_in_owners_tenant
    r = tenant_client(viewer).get(API.person(TestData.DEMO_PERSON_ID))
    assert r.status_code == 200, (
        f"viewer GET person should be 200, got {r.status_code}: {r.text[:200]}"
    )
