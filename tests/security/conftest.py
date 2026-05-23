"""Security domain fixtures."""
from __future__ import annotations

import httpx
import pytest

from tests._fixtures.users import AuthUser
from tests.api_paths import API
from tests.constants import TestConfig, unique_email
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

    signup_unverified(email=viewer_email)
    verify_token = read_email_token(viewer_email)
    httpx.post(
        f"{base_url}{API.VERIFY_EMAIL}",
        json={"token": verify_token},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    viewer_cookies = login_existing(viewer_email)

    invite_token = create_invite(owner, role="viewer", name="Тётя")
    accept_invite(invite_token, cookies=viewer_cookies)

    viewer = AuthUser(
        email=viewer_email,
        password=TestConfig.DEFAULT_PASSWORD,
        slug=owner.slug,
        cookies=viewer_cookies,
    )
    return owner, viewer
