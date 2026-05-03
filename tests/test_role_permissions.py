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

from tests.api_paths import API
from tests.constants import unique_email
from tests.messages import TestData
from tests.timeouts import TIMEOUTS


@pytest.fixture
def viewer_in_owners_tenant(
    signup_via_api, signup_unverified, read_email_token, login_existing,
    create_invite, accept_invite, base_url: str,
):
    """Build a viewer-membership pair: returns (owner, viewer_session).

    `viewer_session` is `{"cookies": ..., "slug": owner.slug}` —
    cookies of the secondary user, slug of the *owner's* tenant
    (cross-tenant access via membership).
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

    return owner, {"cookies": viewer_cookies, "slug": owner.slug}


def test_viewer_can_read_tree(viewer_in_owners_tenant, base_url: str):
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data.

    Was xfail until upstream commit `fded6c7`. Regression-trail.
    """
    _, viewer = viewer_in_owners_tenant

    r = httpx.get(
        f"{base_url}{API.TREE}",
        cookies=viewer["cookies"],
        headers={"X-Tenant-Slug": viewer["slug"]},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, (
        f"viewer GET {API.TREE} should be 200, got {r.status_code}: {r.text[:200]}"
    )


def test_viewer_can_read_person(viewer_in_owners_tenant, base_url: str):
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    _, viewer = viewer_in_owners_tenant

    r = httpx.get(
        f"{base_url}{API.person(TestData.DEMO_PERSON_ID)}",
        cookies=viewer["cookies"],
        headers={"X-Tenant-Slug": viewer["slug"]},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, (
        f"viewer GET person should be 200, got {r.status_code}: {r.text[:200]}"
    )
