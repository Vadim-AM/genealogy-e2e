"""Sharing: создание публичной ссылки, анонимный просмотр, отзыв."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from api import routes, site_api
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.site import ShareListResponse
from pages.share_page import SharePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import Browser

    from fixtures.users import AuthUser


@allure.title("Публичная ссылка: аноним видит карточку, после отзыва -- нет")
def test_owner_shares_card_anon_views_then_revoke_kills_link(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], browser: Browser
) -> None:
    """Полный цикл: создание ссылки → аноним видит карточку → отзыв → ошибка."""
    with step("подготовка: создать публичную ссылку"):
        api = tenant_client(owner_user)

        share = site_api.create_share(api, TestData.DEMO_PERSON_ID)
        share_id = share.id
        share_url = share.url
        should.contain(share_url, "/share/", ErrMsg.share_url_wrong)

    with step("проверка: ссылка в списке без утечки токена"):
        r_list = api.get(routes.SHARE_LIST)
        share_list = expect_response(r_list, label="share list").status_ok().schema(ShareListResponse)
        should.any_match(share_list.items, lambda s: s.id == share_id, ErrMsg.share_not_in_list)
        for s in share_list.items:
            extra = s.model_extra or {}
            should.be_false("url" in extra, ErrMsg.share_token_leaked)

    with step("действие: аноним видит карточку, после отзыва -- ошибку"):
        anon = browser.new_context()
        try:
            page = anon.new_page()
            page.goto(share_url)
            share = SharePage(page)
            share.expect_person_visible(TestData.DEFAULT_FULL_NAME.split()[0])
            share.expect_no_edit_controls()

            expect_response(api.delete(routes.share(share_id)), label="revoke share").status_ok()

            page.goto(share_url)
            share.expect_error_visible()
        finally:
            anon.close()


@allure.title("Список шаринг-ссылок не содержит секретных токенов")
def test_share_list_never_leaks_tokens(owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]) -> None:
    """GET /api/share/list не выдаёт секретный token url."""
    with step("подготовка: создать публичную ссылку"):
        api = tenant_client(owner_user)
        share = site_api.create_share(api, TestData.DEMO_PERSON_ID)
        should.be_true(share.url, ErrMsg.share_url_missing)

    with step("проверка: список не содержит секретных токенов"):
        r_list = api.get(routes.SHARE_LIST)
        share_list = expect_response(r_list, label="share list").status_ok().schema(ShareListResponse)
        should.not_empty(share_list.items, ErrMsg.share_list_empty)
        for item in share_list.items:
            extra = item.model_extra or {}
            should.be_false(extra.get("url"), ErrMsg.share_token_leaked)
