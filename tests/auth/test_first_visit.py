"""First visit after login — F-FV-1..6."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.auth import AccountMe
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser

DEMO_SEED_RING_CARDS = 2


@allure.title("Первый визит отображает дерево с демо-данными")
def test_first_visit_renders_tree_with_demo_seed(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-1, F-FV-2: owner переходит на / и orbit-view рендерит демо-кольцо."""
    with step("действие: переход на главную"):
        tree = pages.navigate_to(TreePage)
        tree.wait_for_page_load()

    with step("проверка: orbit-view отрисовал демо-карточки"):
        tree.expect_tree_rendered(min_cards=DEMO_SEED_RING_CARDS)


@allure.title("Авторизованному пользователю видны навигационные вкладки")
def test_first_visit_shows_authed_tabs(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-4: основные навигационные вкладки видны."""
    with step("действие: переход на главную"):
        tree = pages.navigate_to(TreePage)
        tree.wait_for_page_load()

    with step("проверка: навигационные вкладки видны"):
        expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_sources, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_timeline, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_about, ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Поле поиска отображается в шапке после входа")
def test_first_visit_search_input_visible(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-5: поле поиска видно в шапке для авторизованных."""
    tree = pages.navigate_to(TreePage)
    tree.wait_for_page_load()
    expect(tree.header_search, ErrMsg.element_not_visible).to_be_visible()


@allure.title("Кнопка повтора тура видна на главной после входа")
def test_first_visit_tour_replay_button_visible(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-6: кнопка повтора тура видна."""
    tree = pages.navigate_to(TreePage)
    tree.wait_for_page_load()
    expect(tree.tour_replay_btn, ErrMsg.button_not_visible).to_be_visible()


@allure.title("Эндпоинт /me возвращает slug тенанта после авторизации")
def test_me_endpoint_returns_tenant_after_login(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """F-FV-1: /api/account/me возвращает user + tenant slug."""
    with step("действие: запрос /me"):
        api = tenant_client(owner_user)
        r = api.get(routes.ACCOUNT_ME)

    with step("проверка: slug тенанта совпадает"):
        me_data = expect_response(r, label="GET /me").status_ok().schema(AccountMe)
        should.be_equal(me_data.tenant.slug, owner_user.slug, ErrMsg.me_slug_mismatch)
