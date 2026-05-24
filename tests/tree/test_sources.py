"""Sources journey — attach a historical reference to a person.

Owner opens the demo-self editor, creates+links a source in the
sources-block, sees it attached, unlinks it. Plus a backend lifecycle
for the source record itself (a source has no dedicated edit UI).
"""

from __future__ import annotations

from http import HTTPStatus

import allure
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.err_msg import ErrMsg
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step
from tests._models.site import SourceResponse
from tests.helpers.api import site_api
from tests.pages.person_editor import PersonEditor
from tests.pages.profile_panel import ProfilePanel
from tests.pages.sources_block import SourcesBlock


@allure.title("Владелец привязывает источник к персоне и отвязывает обратно")
def test_owner_attaches_and_unlinks_a_source(
    owner_page: Page, owner_user, tenant_client,
):
    """Owner opens the person editor → creates and links a source →
    it shows attached → unlinks it → it's gone, and the backend agrees."""
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
        linked = api.get(API.person_sources(pid))
        linked_sources = expect_response(linked, label="GET person-sources").status_ok().list_schema(SourceResponse)
        assert any(s.name == src_name for s in linked_sources), \
            f"source not linked backend-side: {[s.name for s in linked_sources]}"

    with step("действие: отвязать источник"):
        with owner_page.expect_response("**/api/person-sources/**"):
            sources.unlink_first()
        expect(sources.items, ErrMsg.wrong_count).to_have_count(0)

    with step("проверка: источник отвязан в бэкенде"):
        after = api.get(API.person_sources(pid))
        after_sources = expect_response(
            after, label="GET person-sources after unlink",
        ).status_ok().list_schema(SourceResponse)
        assert not after_sources, f"source still linked after unlink: {[s.name for s in after_sources]}"


@allure.title("Жизненный цикл источника: создание, переименование, удаление")
def test_source_record_crud_lifecycle(owner_user, tenant_client):
    """Backend lifecycle for a source record itself — there is no
    dedicated UI to edit or delete a source, so this is an invariant
    check: create → rename via PATCH → delete → gone from the list."""
    with step("действие: создать источник"):
        api = tenant_client(owner_user)

        created = site_api.create_source(api, name=TestData.SOURCE_NAME)
        sid = created.id

    with step("действие: переименовать источник"):
        patched = api.patch(API.source(sid), json={"name": TestData.SOURCE_NAME_PATCHED})
        patched_src = expect_response(patched, label="PATCH source").status_ok().schema(SourceResponse)
        assert patched_src.name == TestData.SOURCE_NAME_PATCHED, \
            f"patched name: expected {TestData.SOURCE_NAME_PATCHED!r}, got {patched_src.name!r}"

    with step("действие: удалить источник"):
        deleted = api.delete(API.source(sid))
        expect_response(deleted, label="DELETE source").status(HTTPStatus.NO_CONTENT)

    with step("проверка: источник отсутствует в списке"):
        sources = site_api.get_sources(api)
        assert not any(s.id == sid for s in sources), \
            "deleted source still appears in GET /api/sources"
