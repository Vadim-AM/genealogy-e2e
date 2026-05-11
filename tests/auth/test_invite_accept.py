"""Invite acceptance flow — TC-INV-001, BUG-UX-003 user-flow E2E.

Все assertions через UI. Acceptance — это `#title`/`#msg`/`#link`
на `/invite-accept` (см. `invite-accept.html`) после fetch POST на
`/api/account/tenant/invites/:token/accept`. Тесты не читают response
body — проверяют user-visible эффект на странице (success copy +
link to tree).

Note: creation of invite — единственный API hop. `OwnerPage` POM
не имеет стабильного helper'а для invite-creation UI (Rule #3 в
CLAUDE.md: 4-selector fallback chain — anti-pattern). Когда invite
UI получит `data-invite-url` surface, заменить `api.post` на UI flow.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.constants import make_email
from tests.messages import Invite, TestData, t
from tests.pages.invite_accept_page import InviteAcceptPage


def test_invitee_lands_on_accept_page_sees_success_with_tenant_name(
    auth_context_factory, owner_user, signup_via_api, tenant_client,
):
    """TC-INV-001: invitee opens `/invite-accept?token=` → page auto-fetch'ит
    accept → видит «Готово!» + tenant_display_name + ссылку «Открыть древо».

    UI-flow ловит regression на:
    - success copy не отрендерилась (показывает stale «проверяем токен»);
    - tenant_display_name не подставлен (показывает голый slug);
    - кнопка «Открыть древо» не появилась или указывает не на /.
    """
    viewer_email = make_email("viewer")
    api = tenant_client(owner_user)
    r = api.post(API.TENANT_INVITES, json={"email": viewer_email, "role": "editor"})
    r.raise_for_status()
    invite_token = r.json()["token"]

    invitee = signup_via_api(email=viewer_email)
    ctx = auth_context_factory(invitee, with_tenant_header=False)
    page = ctx.new_page()

    invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    # Success title + tenant_display_name в #msg.
    expect(invite_page.title_el).to_contain_text(t(Invite.ACCEPT_SUCCESS_TITLE))
    # display_name = full_name owner'а (выставлен при signup).
    expect(invite_page.message).to_contain_text(TestData.DEFAULT_FULL_NAME)

    # «Открыть древо» link появилась и ведёт на /.
    link = invite_page.link
    expect(link).to_be_visible()
    expect(link).to_have_text(t(Invite.OPEN_TREE_LINK))
    href = link.get_attribute("href") or ""
    assert href in ("/", ""), f"open-tree link must point to /; got {href!r}"

    page.close()


def test_invitee_clicks_open_tree_lands_on_tree_with_authed_indicator(
    auth_context_factory, owner_user, signup_via_api, tenant_client,
):
    """Full continuation: click «Открыть древо» → / loads с авторизованным
    invitee'ом (его имя в `#authIndicator .auth-name`).

    Catches: redirect ломается, session-cookie не переключилась на принятый
    tenant, auth indicator показывает guest несмотря на 200 accept.
    """
    viewer_email = make_email("viewer2")
    api = tenant_client(owner_user)
    r = api.post(API.TENANT_INVITES, json={"email": viewer_email, "role": "editor"})
    r.raise_for_status()
    invite_token = r.json()["token"]

    invitee = signup_via_api(email=viewer_email)
    ctx = auth_context_factory(invitee, with_tenant_header=False)
    page = ctx.new_page()

    InviteAcceptPage(page).open_with_token(invite_token)
    open_link = page.locator("#link")
    expect(open_link).to_be_visible()
    open_link.click()

    page.wait_for_url("**/")
    expect(page.locator("#authIndicator .auth-name")).to_have_text(
        TestData.DEFAULT_FULL_NAME
    )
    page.close()


def test_owner_opens_own_invite_sees_warning_with_display_name(
    owner_page: Page, owner_user, tenant_client,
):
    """TC-INVITE-1 + BUG-UX-003: owner открывает собственный invite-link
    → видит warning с tenant *display_name* (full_name из signup),
    а не slug-URL.

    `display_name` отдельное поле от `family_name`, выставляется на
    signup'е (auth_v2/router.py:316,357) и выходит в «уже владелец»
    через tenant_invites.py:253.
    """
    api = tenant_client(owner_user)
    r = api.post(API.TENANT_INVITES, json={"email": make_email("self"), "role": "viewer"})
    r.raise_for_status()
    invite_token = r.json()["token"]

    invite_page = InviteAcceptPage(owner_page).open_with_token(invite_token)

    expect(invite_page.message).to_contain_text(t(Invite.OWNER_WARNING))

    msg_text = invite_page.message.text_content() or ""
    expected_display = TestData.DEFAULT_FULL_NAME
    assert expected_display in msg_text, (
        f"display_name {expected_display!r} not in owner-warning: {msg_text!r}"
    )
    assert owner_user.slug not in msg_text, (
        f"raw slug {owner_user.slug!r} leaked into owner-warning: {msg_text!r}"
    )


def test_anonymous_invitee_sees_login_links_with_token_in_next(
    page: Page, owner_user, tenant_client,
):
    """TC-INVITE-2: anonymous visitor видит prompt с links на `/login`
    и `/signup`, оба preserve token через `?next=/invite-accept?token=…`.
    """
    api = tenant_client(owner_user)
    r = api.post(API.TENANT_INVITES, json={"email": make_email("guest-invitee"), "role": "viewer"})
    r.raise_for_status()
    invite_token = r.json()["token"]

    invite_page = InviteAcceptPage(page).open_with_token(invite_token)
    # Substring «войди» покрывает «войдите», «войду» — verb-forms varies.
    expect(invite_page.message).to_contain_text("войди")

    login_link = page.get_by_role("link", name="ойди", exact=False).first
    signup_link = page.get_by_role("link", name="егистр", exact=False).first
    expect(login_link).to_be_visible()
    expect(signup_link).to_be_visible()

    login_href = login_link.get_attribute("href") or ""
    signup_href = signup_link.get_attribute("href") or ""
    assert invite_token in login_href, (
        f"login link must carry invite token: {login_href!r}"
    )
    assert invite_token in signup_href, (
        f"signup link must carry invite token: {signup_href!r}"
    )
