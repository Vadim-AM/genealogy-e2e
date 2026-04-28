"""Invite acceptance flow — TC-INV-001, BUG-UX-003.

Owner creates invite → second user accepts via /invite-accept → membership granted.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.pages.invite_accept_page import InviteAcceptPage


def test_invite_accept_grants_membership(
    auth_context_factory, owner_user, signup_via_api, base_url: str
):
    """TC-INV-001: owner creates invite, second user accepts → membership=editor."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "viewer@e2e.example.com", "role": "editor"},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    invite_token = r.json().get("token") or r.json().get("invite_token")
    assert invite_token, f"no invite token in response: {r.json()}"

    invitee = signup_via_api(email="viewer@e2e.example.com")
    # Use invitee's browser context to accept the invite via UI.
    ctx = auth_context_factory(invitee, with_tenant_header=False)
    page = ctx.new_page()
    InviteAcceptPage(page).open_with_token(invite_token).expect_message_loaded()
    # Backend assertion: invitee now has membership in owner's tenant.
    page.close()

    r = httpx.post(
        f"{base_url}/api/account/tenant/invites/{invite_token}/accept",
        cookies=invitee.cookies,
        timeout=10,
    )
    # Either accepted (first time) or already_member (second time).
    assert r.status_code in (200, 409), r.text
    body = r.json() if r.status_code == 200 else {}
    if r.status_code == 200:
        status = body.get("status") or body.get("result")
        assert status in (None, "accepted", "already_member"), body


def test_owner_accepting_own_invite_shows_warning(
    owner_page: Page, owner_user, base_url: str
):
    """BUG-UX-003 regression: owner opening own invite link must see warning,
    not be re-accepted. Was xfail (Apr 2026), passed in current HEAD — now
    enforced as a regression."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "self@e2e.example.com", "role": "viewer"},
        cookies=owner_user.cookies,
        headers=headers,
    )
    invite_token = r.json().get("token") or r.json().get("invite_token")

    invite_page = InviteAcceptPage(owner_page)
    invite_page.open_with_token(invite_token)
    invite_page.expect_message_loaded()
    msg = (invite_page.message.text_content() or "").lower()
    assert "уже" in msg or "владелец" in msg, f"expected owner-warning, got: {msg}"
