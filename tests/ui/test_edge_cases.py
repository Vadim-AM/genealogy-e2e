"""Edge cases per docs/test-plan.md TC-EDGE-001..005."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser


@allure.title("Edge: переход по несуществующему профилю не ломает UI")
def test_f5_on_nonexistent_profile_id_does_not_crash(pages: PageFactory) -> None:
    """TC-EDGE-004: F5 on /#/p/<unknown> shows tree, no JS crash."""
    tree = pages.create(TreePage).goto_hash("#/p/nonexistent_xyz_123")
    expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Edge: персона с единственным полем name корректно читается")
def test_old_person_with_only_name_field_renders(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-EDGE-001: a person record with only `name` (no surname/given) — accessible."""
    api = tenant_client(owner_user)

    with step("действие: создать персону с единственным полем name"):
        payload = {
            "id": "edge-old-name",
            "name": "Иванов Иван Петрович",
            "branch": "subject",
            "gender": "m",
        }
        r = api.post(routes.PEOPLE, json=payload)
        expect_response(
            r,
            label=f"POST {routes.PEOPLE} legacy payload",
        ).status(HTTPStatus.OK, HTTPStatus.CREATED)

    with step("проверка: имя сохранилось при чтении"):
        r = api.get(routes.person("edge-old-name"))
        data = expect_response(r, label="read legacy person").status_ok().data
        name = data.get("name") or ""
        should.contain(name, "Иван", ErrMsg.canonical_name_wrong)


@allure.title("Edge: /api/health доступен без авторизации и отдаёт ok")
def test_health_endpoint_does_not_require_auth(base_url: str) -> None:
    """Smoke: /api/health is public (no auth), reports status ok."""
    with step("действие: запросить /api/health без авторизации"):
        r = httpx.get(f"{base_url}{routes.HEALTH}")

    with step("проверка: статус ok"):
        expect_response(r, label="health").status_ok().json_eq("status", "ok")
