"""Sources: привязка/отвязка источника к персоне + CRUD lifecycle."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes, site_api
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.site import SourceResponse
from pages.person_editor import PersonEditor
from pages.profile_panel import ProfilePanel
from pages.sources_block import SourcesBlock
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Владелец привязывает источник к персоне и отвязывает обратно")
def test_owner_attaches_and_unlinks_a_source(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Привязать источник → виден в UI и API → отвязать → нет."""
    with step("подготовка: открыть редактор персоны"):
        pid = TestData.DEMO_PERSON_ID
        api = tenant_client(owner_user)

        panel = ProfilePanel.navigate_to(owner_page, pid)
        panel.open_editor()
        PersonEditor(owner_page).expect_visible()
        sources = SourcesBlock(owner_page)

    with step("действие: привязать источник"):
        src_name = "Метрическая книга, 1890"
        with owner_page.expect_response("**/api/person-sources"):
            sources.create_and_link(name=src_name)
        sources.expect_attached(src_name)

    with step("проверка: источник привязан в бэкенде"):
        linked = api.get(routes.person_sources(pid))
        linked_sources = expect_response(linked, label="GET person-sources").status_ok().list_schema(SourceResponse)
        should.any_match(linked_sources, lambda s: s.name == src_name, ErrMsg.source_not_linked)

    with step("действие: отвязать источник"):
        with owner_page.expect_response("**/api/person-sources/**"):
            sources.unlink_first()
        expect(sources.items, ErrMsg.wrong_count).to_have_count(0)

    with step("проверка: источник отвязан в бэкенде"):
        after = api.get(routes.person_sources(pid))
        after_sources = (
            expect_response(
                after,
                label="GET person-sources after unlink",
            )
            .status_ok()
            .list_schema(SourceResponse)
        )
        should.be_empty(after_sources, ErrMsg.source_still_linked)


@allure.title("Жизненный цикл источника: создание, переименование, удаление")
def test_source_record_crud_lifecycle(owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]) -> None:
    """Create → PATCH rename → DELETE → отсутствует в списке."""
    with step("действие: создать источник"):
        api = tenant_client(owner_user)

        created = site_api.create_source(api, name=TestData.SOURCE_NAME)
        sid = should.not_none(created.id, ErrMsg.response_field_wrong)

    with step("действие: переименовать источник"):
        patched = api.patch(routes.source(sid), json={"name": TestData.SOURCE_NAME_PATCHED})
        patched_src = expect_response(patched, label="PATCH source").status_ok().schema(SourceResponse)
        should.be_equal(patched_src.name, TestData.SOURCE_NAME_PATCHED, ErrMsg.source_name_wrong)

    with step("действие: удалить источник"):
        deleted = api.delete(routes.source(sid))
        expect_response(deleted, label="DELETE source").status(HTTPStatus.NO_CONTENT)

    with step("проверка: источник отсутствует в списке"):
        sources = site_api.get_sources(api)
        should.be_false(any(s.id == sid for s in sources), ErrMsg.source_not_deleted)
