"""Onboarding demo-data journeys — удаление или сохранение демо-данных."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from api import person_api
from assertions.base import should
from framework.step import step
from pages.confirm_dialog import ConfirmDialog
from pages.owner_page import OwnerPage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser


@allure.title("Владелец удаляет демо-родственников из дерева")
def test_owner_clears_demo_relatives(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], pages: PageFactory
) -> None:
    """Owner стирает демо-родственников через настройки."""
    with step("подготовка: проверка наличия демо-данных"):
        api = tenant_client(owner_user)
        before = person_api.get_people(api)
        should.greater(len(before), 1, ErrMsg.demo_seed_required)

    with step("действие: удаление демо-родственников через UI"):
        owner = pages.navigate_to(OwnerPage)
        dialog = ConfirmDialog(owner_page)
        with owner_page.expect_response("**/api/onboarding/clear-demo"):
            owner.click_clear_demo()
            dialog.expect_visible()
            dialog.confirm()

    with step("проверка: количество персон уменьшилось"):
        after = person_api.get_people(api)
        should.less(len(after), len(before), ErrMsg.demo_not_cleared)


@allure.title("Владелец сохраняет демо-данные как шаблон для дерева")
def test_owner_keeps_demo_as_template(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], pages: PageFactory
) -> None:
    """Owner сохраняет демо-данные как шаблон для дерева."""
    with step("подготовка: проверка наличия демо-данных"):
        api = tenant_client(owner_user)
        before = person_api.get_people(api)
        should.greater(len(before), 1, ErrMsg.demo_seed_required)

    with step("действие: сохранение демо-данных как шаблона"):
        owner = pages.navigate_to(OwnerPage)
        dialog = ConfirmDialog(owner_page)
        with owner_page.expect_response("**/api/onboarding/keep-demo"):
            owner.click_keep_demo()
            dialog.expect_visible()
            dialog.confirm()

    with step("проверка: количество персон не изменилось"):
        after = person_api.get_people(api)
        should.be_equal(len(after), len(before), ErrMsg.demo_not_preserved)
