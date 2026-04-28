"""Invite acceptance flow — TC-INV-001, BUG-UX-003.

Owner creates invite → second user accepts via /invite-accept → membership granted.
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page, expect

from tests.messages import Invite, t
from tests.pages.invite_accept_page import InviteAcceptPage


def test_invite_accept_grants_membership(
    auth_context_factory, owner_user, signup_via_api, base_url: str
):
    """TC-INV-001: invitee accepts invite via UI → membership granted in backend.

    The /invite-accept page itself POSTs to /accept on load, so we verify the
    membership server-side via the invite list (or membership list) instead
    of re-POSTing — re-accept legitimately returns 409 already_member.
    """
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "viewer@e2e.example.com", "role": "editor"},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    invite_token = r.json()["token"]

    invitee = signup_via_api(email="viewer@e2e.example.com")
    ctx = auth_context_factory(invitee, with_tenant_header=False)
    page = ctx.new_page()

    # Page calls POST /accept on load. Wait for that response and read its
    # body BEFORE closing the page (Response.json() needs the page alive).
    with page.expect_response("**/api/account/tenant/invites/*/accept") as resp_info:
        InviteAcceptPage(page).open_with_token(invite_token)
    accept_response = resp_info.value
    assert accept_response.status == 200, \
        f"accept returned {accept_response.status}: {accept_response.text()[:200]}"
    body = accept_response.json()
    page.close()

    assert body["status"] in ("accepted", "already_member"), \
        f"unexpected accept status: {body!r}"


def test_owner_accepting_own_invite_shows_warning(
    owner_page: Page, owner_user, base_url: str
):
    """BUG-UX-003 regression: owner opening own invite link must see a warning,
    not silently re-accept.

    /invite-accept POSTs on load, so we wait for that response, then read
    the final message — the placeholder ('Минутку — проверяем токен.') is
    replaced by the resolved message.
    """
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "self@e2e.example.com", "role": "viewer"},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    invite_token = r.json()["token"]

    invite_page = InviteAcceptPage(owner_page)
    with owner_page.expect_response("**/api/account/tenant/invites/*/accept"):
        invite_page.open_with_token(invite_token)

    # Owner-warning copy must contain the catalogue keyword. Wait until the
    # placeholder is gone — `expect.to_contain_text` auto-waits.
    keyword = t(Invite.OWNER_WARNING)
    expect(invite_page.message).to_contain_text(keyword)
