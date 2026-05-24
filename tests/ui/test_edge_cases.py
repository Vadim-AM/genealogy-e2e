"""Edge cases per docs/test-plan.md TC-EDGE-001..005."""

from __future__ import annotations

from http import HTTPStatus

import allure
import httpx
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg


@allure.title("Edge: переход по несуществующему профилю не ломает UI")
def test_f5_on_nonexistent_profile_id_does_not_crash(owner_page: Page) -> None:
    """TC-EDGE-004: F5 on /#/p/<unknown> shows tree, no JS crash."""
    tree = TreePage(owner_page)
    owner_page.goto("/#/p/nonexistent_xyz_123")
    tree.wait_for_page_load()
    expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Edge: персона с единственным полем name корректно читается")
def test_old_person_with_only_name_field_renders(owner_user, tenant_client) -> None:
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
            r, label=f"POST {routes.PEOPLE} legacy payload",
        ).status(HTTPStatus.OK, HTTPStatus.CREATED)

    with step("проверка: имя сохранилось при чтении"):
        r = api.get(routes.person("edge-old-name"))
        r.raise_for_status()
        name = r.json().get("name") or ""
        should.contain(name, "Иван", ErrMsg.canonical_name_wrong)


@allure.title("Edge: /api/health доступен без авторизации и отдаёт ok")
def test_health_endpoint_does_not_require_auth(base_url: str) -> None:
    """Smoke: /api/health is public (no auth), reports status ok."""
    with step("действие: запросить /api/health без авторизации"):
        r = httpx.get(f"{base_url}{routes.HEALTH}")
        r.raise_for_status()

    with step("проверка: статус ok"):
        should.be_equal(r.json().get("status"), "ok", ErrMsg.health_status_wrong)
