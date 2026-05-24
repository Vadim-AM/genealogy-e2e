"""Onboarding demo-data journeys — clear or keep the seeded demo relatives.

A fresh tenant seeds demo people (Иван, Мария …). In owner settings the
owner chooses to erase them outright or keep them as an editable
template. Two tenants — each test gets its own owner — so the two
mutually-exclusive choices are exercised independently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from tests.api_paths import API
from tests.pages.confirm_dialog import ConfirmDialog
from tests.step import step

if TYPE_CHECKING:
    from playwright.sync_api import Page


@allure.title("Владелец удаляет демо-родственников из дерева")
def test_owner_clears_demo_relatives(owner_page: Page, owner_user, tenant_client):
    """Owner opens settings → 'Стереть демо-родственников' → confirms →
    the demo people are removed from the tree."""
    with step("подготовка: проверка наличия демо-данных"):
        api = tenant_client(owner_user)
        before = api.get(API.TREE).json()["people"]
        assert len(before) > 1, "a fresh tenant seeds demo relatives"

    with step("действие: удаление демо-родственников через UI"):
        owner_page.goto("/owner")
        owner_page.wait_for_load_state("domcontentloaded")
        dialog = ConfirmDialog(owner_page)
        with owner_page.expect_response("**/api/onboarding/clear-demo"):
            owner_page.locator("#clearDemo").click()
            dialog.expect_visible()
            dialog.confirm()

    with step("проверка: количество персон уменьшилось"):
        after = api.get(API.TREE).json()["people"]
        assert len(after) < len(before), \
            f"demo relatives must be gone: {len(before)} → {len(after)}"


@allure.title("Владелец сохраняет демо-данные как шаблон для дерева")
def test_owner_keeps_demo_as_template(owner_page: Page, owner_user, tenant_client):
    """Owner opens settings → 'Использовать как шаблон' → confirms →
    the tree structure stays (people are kept, not deleted)."""
    with step("подготовка: проверка наличия демо-данных"):
        api = tenant_client(owner_user)
        before = api.get(API.TREE).json()["people"]
        assert len(before) > 1, "a fresh tenant seeds demo relatives"

    with step("действие: сохранение демо-данных как шаблона"):
        owner_page.goto("/owner")
        owner_page.wait_for_load_state("domcontentloaded")
        dialog = ConfirmDialog(owner_page)
        with owner_page.expect_response("**/api/onboarding/keep-demo"):
            owner_page.locator("#keepDemo").click()
            dialog.expect_visible()
            dialog.confirm()

    with step("проверка: количество персон не изменилось"):
        after = api.get(API.TREE).json()["people"]
        assert len(after) == len(before), \
            f"keep-as-template must preserve the structure: {len(before)} → {len(after)}"
