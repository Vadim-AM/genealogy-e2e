"""Security domain fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from api import routes
from config.constants import TestConfig, unique_email
from fixtures.users import AuthUser

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def viewer_in_owners_tenant(
    signup_via_api: Callable[..., AuthUser],
    signup_unverified: Callable[..., str],
    read_email_token: Callable[[str], str],
    login_existing: Callable[..., dict[str, str]],
    create_invite: Callable[..., str],
    accept_invite: Callable[..., dict[str, str]],
    base_url: str,
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
        f"{base_url}{routes.VERIFY_EMAIL}",
        json={"token": verify_token},
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
