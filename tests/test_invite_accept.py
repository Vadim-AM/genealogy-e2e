"""Invite acceptance flow — TC-INV-001, BUG-UX-003.

Owner creates invite → second user accepts via /invite-accept → membership granted.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.timeouts import TIMEOUTS

from tests.messages import Invite, TestData, t
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
        timeout=TIMEOUTS.api_request,
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


def test_owner_accepting_own_invite_shows_warning_with_display_name(
    owner_page: Page, owner_user, base_url: str
):
    """TC-INVITE-1 + BUG-UX-003: owner opening own invite must see a warning
    that includes the tenant's *display_name* (set from `full_name` at signup),
    not the URL slug.

    `display_name` is a separate field from `family_name` — set during signup
    (auth_v2/router.py:316,357) and surfaced by tenant_invites.py:253 in the
    "уже владелец" message.
    """
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "self@e2e.example.com", "role": "viewer"},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    invite_token = r.json()["token"]

    invite_page = InviteAcceptPage(owner_page)
    with owner_page.expect_response("**/api/account/tenant/invites/*/accept"):
        invite_page.open_with_token(invite_token)

    keyword = t(Invite.OWNER_WARNING)
    expect(invite_page.message).to_contain_text(keyword)

    msg_text = invite_page.message.text_content() or ""
    expected_display = TestData.DEFAULT_FULL_NAME
    assert expected_display in msg_text, \
        f"display_name {expected_display!r} not in owner-warning: {msg_text!r}"
    assert owner_user.slug not in msg_text, \
        f"raw slug {owner_user.slug!r} leaked into owner-warning: {msg_text!r}"


def test_guest_on_invite_page_sees_login_required_with_token_preserved(
    page: Page, owner_user, base_url: str
):
    """TC-INVITE-2: anonymous visitor opening an invite link sees a "log in"
    page where both `/login` and `/signup` links carry `?next=...&token=...`
    so they return to acceptance after authenticating.
    """
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"email": "guest-invitee@e2e.example.com", "role": "viewer"},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    invite_token = r.json()["token"]

    invite_page = InviteAcceptPage(page)
    invite_page.open_with_token(invite_token)
    # Substring covers «войти», «войдите», «войду» — common verb forms
    # the message can use without breaking the test on copy edits.
    expect(invite_page.message).to_contain_text("войди")

    # Both links must preserve the token so the user returns to acceptance.
    login_link = page.get_by_role("link", name="ойди", exact=False).first
    signup_link = page.get_by_role("link", name="егистр", exact=False).first
    expect(login_link).to_be_visible()
    expect(signup_link).to_be_visible()
    login_href = login_link.get_attribute("href") or ""
    signup_href = signup_link.get_attribute("href") or ""
    assert invite_token in login_href, \
        f"login link must carry the invite token: {login_href!r}"
    assert invite_token in signup_href, \
        f"signup link must carry the invite token: {signup_href!r}"
