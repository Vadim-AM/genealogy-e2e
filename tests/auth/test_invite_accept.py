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

import allure
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.constants import make_email
from tests.helpers.auth.auth_ui import auth_name
from tests.messages import Invite, TestData, t
from tests.pages.invite_accept_page import InviteAcceptPage
from tests.step import step


@allure.title("Приглашённый видит успех с именем древа на странице принятия")
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
    with step("подготовка: создание приглашения и signup invitee"):
        viewer_email = make_email("viewer")
        api = tenant_client(owner_user)
        r = api.post(API.TENANT_INVITES, json={"email": viewer_email, "role": "editor"})
        r.raise_for_status()
        invite_token = r.json()["token"]

        invitee = signup_via_api(email=viewer_email)
        ctx = auth_context_factory(invitee, with_tenant_header=False)
        page = ctx.new_page()

    with step("действие: открытие страницы принятия приглашения"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: success-копия с именем древа и ссылка на дерево"):
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


@allure.title("Клик 'Открыть древо' ведёт на главную с авторизацией")
def test_invitee_clicks_open_tree_lands_on_tree_with_authed_indicator(
    auth_context_factory, owner_user, signup_via_api, tenant_client,
):
    """Full continuation: click «Открыть древо» → / loads с авторизованным
    invitee'ом (его имя в `#authIndicator .auth-name`).

    Catches: redirect ломается, session-cookie не переключилась на принятый
    tenant, auth indicator показывает guest несмотря на 200 accept.
    """
    with step("подготовка: создание приглашения и signup invitee"):
        viewer_email = make_email("viewer2")
        api = tenant_client(owner_user)
        r = api.post(API.TENANT_INVITES, json={"email": viewer_email, "role": "editor"})
        r.raise_for_status()
        invite_token = r.json()["token"]

        invitee = signup_via_api(email=viewer_email)
        ctx = auth_context_factory(invitee, with_tenant_header=False)
        page = ctx.new_page()

    with step("действие: принятие приглашения и клик 'Открыть древо'"):
        InviteAcceptPage(page).open_with_token(invite_token)
        open_link = page.locator("#link")
        expect(open_link).to_be_visible()
        open_link.click()

    with step("проверка: redirect на главную с авторизованным пользователем"):
        page.wait_for_url("**/")
        expect(auth_name(page)).to_have_text(
            TestData.DEFAULT_FULL_NAME
        )

    page.close()


@allure.title("Владелец открывает своё приглашение и видит предупреждение")
def test_owner_opens_own_invite_sees_warning_with_display_name(
    owner_page: Page, owner_user, tenant_client,
):
    """TC-INVITE-1 + BUG-UX-003: owner открывает invite, выписанный на
    *свой собственный* email → видит warning «вы и так владелец древа
    «<display_name>»» (full_name из signup), а не slug-URL.

    Контракт изменён в v2-Phase1: accept теперь email-bound. Если
    авторизованный owner открывает invite на ЧУЖОЙ email — backend
    отбивает 403 «приглашение для другого email-адреса» (anti-forward
    защита, tenant_invites.py:270). Чтобы дойти до owner-warning,
    invite должен быть на email самого owner'а → email совпадает →
    `already_member`/`role=owner` → invite-accept.js рисует «Это ваше
    древо» + tenant_display_name.
    """
    with step("подготовка: создание invite на свой email"):
        api = tenant_client(owner_user)
        r = api.post(API.TENANT_INVITES, json={"email": owner_user.email, "role": "viewer"})
        r.raise_for_status()
        invite_token = r.json()["token"]

    with step("действие: владелец открывает своё приглашение"):
        invite_page = InviteAcceptPage(owner_page).open_with_token(invite_token)

    with step("проверка: предупреждение с display_name без slug"):
        expect(invite_page.message).to_contain_text(t(Invite.OWNER_WARNING))

        msg_text = invite_page.message.text_content() or ""
        expected_display = TestData.DEFAULT_FULL_NAME
        assert expected_display in msg_text, (
            f"display_name {expected_display!r} not in owner-warning: {msg_text!r}"
        )
        assert owner_user.slug not in msg_text, (
            f"raw slug {owner_user.slug!r} leaked into owner-warning: {msg_text!r}"
        )


@allure.title("Неавторизованный видит ссылки входа/регистрации с токеном")
def test_anonymous_invitee_sees_login_links_with_token_in_next(
    page: Page, owner_user, tenant_client,
):
    """TC-INVITE-2: anonymous visitor + **email-less** invite видит prompt
    с links на `/login` и `/signup`, оба preserve token через
    `?next=/invite-accept?token=…`.

    Контракт изменён в v2-Phase1: invite *с* email + неавторизованный
    recipient = magic-link (backend сам создаёт passwordless user,
    auto-accept — см. test_anonymous_emailed_invite_is_magic_link_auto_accepted).
    Login-prompt путь (401) теперь срабатывает ТОЛЬКО для invite **без**
    email (`CreateInviteRequest.email` опционален). Поэтому здесь invite
    создаётся без email.
    """
    with step("подготовка: создание приглашения без email"):
        api = tenant_client(owner_user)
        r = api.post(API.TENANT_INVITES, json={"role": "viewer"})
        r.raise_for_status()
        invite_token = r.json()["token"]

    with step("действие: анонимный пользователь открывает invite"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: ссылки входа/регистрации с токеном в next"):
        expect(invite_page.message).to_contain_text(t(Invite.LOGIN_REQUIRED_MSG))

        login_link = page.get_by_role("link", name=t(Invite.LOGIN_LINK), exact=False).first
        signup_link = page.get_by_role("link", name=t(Invite.SIGNUP_LINK), exact=False).first
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


@allure.title("Email-приглашение работает как magic-link без логина")
def test_anonymous_emailed_invite_is_magic_link_auto_accepted(
    page: Page, owner_user, tenant_client,
):
    """v2-Phase1 H5 (new contract): an *emailed* invite opened by an
    anonymous visitor is a magic-link — the unique 192-bit token is the
    email-ownership proof, so the backend creates a passwordless user and
    auto-accepts. No login prompt. invite-accept.js renders the fresh-accept
    success ("Готово!" + «Вы добавлены в древо … с ролью …»).

    Guards the security-relevant behaviour change: clicking an emailed
    invite link grants access without an interactive auth step.
    """
    with step("подготовка: создание email-приглашения"):
        viewer_email = make_email("magic-invitee")
        api = tenant_client(owner_user)
        r = api.post(API.TENANT_INVITES, json={"email": viewer_email, "role": "viewer"})
        r.raise_for_status()
        invite_token = r.json()["token"]

    with step("действие: анонимный пользователь открывает magic-link"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: auto-accept без логина, success с display_name"):
        expect(invite_page.title_el).to_contain_text(t(Invite.ACCEPT_SUCCESS_TITLE))
        expect(invite_page.message).to_contain_text(t(Invite.ADDED_TO_TREE))
        # Tenant display_name (owner full_name) rendered, not raw slug.
        expect(invite_page.message).to_contain_text(TestData.DEFAULT_FULL_NAME)
        assert owner_user.slug not in (invite_page.message.text_content() or ""), \
            "raw slug leaked into magic-link success copy"
