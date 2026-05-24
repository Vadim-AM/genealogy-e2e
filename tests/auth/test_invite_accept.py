"""Invite acceptance flow — TC-INV-001, BUG-UX-003 user-flow E2E."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import auth_api
from assertions.base import should
from config.constants import unique_email
from framework.step import step
from pages.invite_accept_page import InviteAcceptPage
from pages.tree_page import TreePage
from src.texts import ErrMsg, Invite, TestData, t

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import BrowserContext

    from fixtures.users import AuthUser


@allure.title("Приглашённый видит успех с именем древа на странице принятия")
def test_invitee_lands_on_accept_page_sees_success_with_tenant_name(
    auth_context_factory: Callable[..., BrowserContext],
    owner_user: AuthUser,
    signup_via_api: Callable[..., AuthUser],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """TC-INV-001: invitee открывает invite → видит «Готово!» + ссылку на дерево."""
    with step("подготовка: создание приглашения и signup invitee"):
        viewer_email = unique_email("viewer")
        api = tenant_client(owner_user)
        invite = auth_api.create_invite(api, email=viewer_email, role="editor")
        invite_token = invite.token

        invitee = signup_via_api(email=viewer_email)
        ctx = auth_context_factory(invitee, with_tenant_header=False)
        page = ctx.new_page()

    with step("действие: открытие страницы принятия приглашения"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: success-копия с именем древа и ссылка на дерево"):
        expect(invite_page.title_el, ErrMsg.invite_title_wrong).to_contain_text(t(Invite.ACCEPT_SUCCESS_TITLE))
        expect(invite_page.message, ErrMsg.invite_message_wrong).to_contain_text(TestData.DEFAULT_FULL_NAME)

        expect(invite_page.link, ErrMsg.invite_link_not_visible).to_be_visible()
        expect(invite_page.link, ErrMsg.wrong_text_content).to_have_text(t(Invite.OPEN_TREE_LINK))
        href = invite_page.get_link_href()
        should.be_in(href, ("/", ""), ErrMsg.invite_href_wrong)

    page.close()


@allure.title("Клик 'Открыть древо' ведёт на главную с авторизацией")
def test_invitee_clicks_open_tree_lands_on_tree_with_authed_indicator(
    auth_context_factory: Callable[..., BrowserContext],
    owner_user: AuthUser,
    signup_via_api: Callable[..., AuthUser],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """Клик «Открыть древо» → / с авторизованным invitee в auth indicator."""
    with step("подготовка: создание приглашения и signup invitee"):
        viewer_email = unique_email("viewer2")
        api = tenant_client(owner_user)
        invite = auth_api.create_invite(api, email=viewer_email, role="editor")
        invite_token = invite.token

        invitee = signup_via_api(email=viewer_email)
        ctx = auth_context_factory(invitee, with_tenant_header=False)
        page = ctx.new_page()

    with step("действие: принятие приглашения и клик 'Открыть древо'"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)
        expect(invite_page.link, ErrMsg.invite_link_not_visible).to_be_visible()
        invite_page.click_open_tree()

    with step("проверка: redirect на главную с авторизованным пользователем"):
        page.wait_for_url("**/")
        tree = TreePage(page)
        expect(tree.auth_user_name, ErrMsg.auth_name_wrong).to_have_text(TestData.DEFAULT_FULL_NAME)

    page.close()


@allure.title("Владелец открывает своё приглашение и видит предупреждение")
def test_owner_opens_own_invite_sees_warning_with_display_name(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-INVITE-1 + BUG-UX-003: owner открывает свой invite → warning с display_name."""
    with step("подготовка: создание invite на свой email"):
        api = tenant_client(owner_user)
        invite = auth_api.create_invite(api, email=owner_user.email, role="viewer")
        invite_token = invite.token

    with step("действие: владелец открывает своё приглашение"):
        invite_page = InviteAcceptPage(owner_page).open_with_token(invite_token)

    with step("проверка: предупреждение с display_name без slug"):
        expect(invite_page.message, ErrMsg.invite_message_wrong).to_contain_text(t(Invite.OWNER_WARNING))

        msg_text = invite_page.message.text_content() or ""
        should.contain(msg_text, TestData.DEFAULT_FULL_NAME, ErrMsg.display_name_not_in_message)
        should.not_contain(msg_text, owner_user.slug, ErrMsg.slug_leaked_in_message)


@allure.title("Неавторизованный видит ссылки входа/регистрации с токеном")
def test_anonymous_invitee_sees_login_links_with_token_in_next(
    page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-INVITE-2: anonymous + invite без email → prompt с login/signup ссылками."""
    with step("подготовка: создание приглашения без email"):
        api = tenant_client(owner_user)
        invite = auth_api.create_invite(api, role="viewer")
        invite_token = invite.token

    with step("действие: анонимный пользователь открывает invite"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: ссылки входа/регистрации с токеном в next"):
        expect(invite_page.message, ErrMsg.invite_message_wrong).to_contain_text(t(Invite.LOGIN_REQUIRED_MSG))

        expect(invite_page.login_link, ErrMsg.link_not_visible).to_be_visible()
        expect(invite_page.signup_link, ErrMsg.link_not_visible).to_be_visible()

        login_href = invite_page.get_login_href()
        signup_href = invite_page.get_signup_href()
        should.contain(login_href, invite_token, ErrMsg.invite_token_missing_in_href)
        should.contain(signup_href, invite_token, ErrMsg.invite_token_missing_in_href)


@allure.title("Email-приглашение работает как magic-link без логина")
def test_anonymous_emailed_invite_is_magic_link_auto_accepted(
    page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """v2-Phase1 H5: email-invite = magic-link → auto-accept без логина."""
    with step("подготовка: создание email-приглашения"):
        viewer_email = unique_email("magic-invitee")
        api = tenant_client(owner_user)
        invite = auth_api.create_invite(api, email=viewer_email, role="viewer")
        invite_token = invite.token

    with step("действие: анонимный пользователь открывает magic-link"):
        invite_page = InviteAcceptPage(page).open_with_token(invite_token)

    with step("проверка: auto-accept без логина, success с display_name"):
        expect(invite_page.title_el, ErrMsg.invite_title_wrong).to_contain_text(t(Invite.ACCEPT_SUCCESS_TITLE))
        expect(invite_page.message, ErrMsg.invite_message_wrong).to_contain_text(t(Invite.ADDED_TO_TREE))
        expect(invite_page.message, ErrMsg.invite_message_wrong).to_contain_text(TestData.DEFAULT_FULL_NAME)
        should.not_contain(
            invite_page.message.text_content() or "",
            owner_user.slug,
            ErrMsg.slug_leaked_in_message,
        )
