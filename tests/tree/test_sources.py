"""Sources journey — attach a historical reference to a person.

Owner opens the demo-self editor, creates+links a source in the
sources-block, sees it attached, unlinks it. Plus a backend lifecycle
for the source record itself (a source has no dedicated edit UI).
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.person_editor import PersonEditor
from tests.pages.profile_panel import ProfilePanel
from tests.pages.sources_block import SourcesBlock
from tests.response import expect_response


@allure.title("Владелец привязывает источник к персоне и отвязывает его")
def test_owner_attaches_and_unlinks_a_source(
    owner_page: Page, owner_user, tenant_client,
):
    """Owner opens the person editor → creates and links a source →
    it shows attached → unlinks it → it's gone, and the backend agrees."""
    pid = TestData.DEMO_PERSON_ID
    api = tenant_client(owner_user)

    panel = ProfilePanel.navigate_to(owner_page, pid)
    panel.open_editor()
    PersonEditor(owner_page).expect_visible()

    sources = SourcesBlock(owner_page)
    src_name = "Метрическая книга, 1890"
    with owner_page.expect_response("**/api/person-sources"):
        sources.create_and_link(name=src_name)
    sources.expect_attached(src_name)

    linked = api.get(API.person_sources(pid))
    expect_response(linked, label="GET person-sources").status_ok()
    assert any(s["name"] == src_name for s in linked.json()), \
        f"source not linked backend-side: {linked.json()}"

    with owner_page.expect_response("**/api/person-sources/**"):
        sources.unlink_first()
    expect(sources.items).to_have_count(0)

    after = api.get(API.person_sources(pid))
    expect_response(after, label="GET person-sources after unlink").status_ok()
    assert not after.json(), f"source still linked after unlink: {after.json()}"


@allure.title("Жизненный цикл источника: создание, переименование, удаление")
def test_source_record_crud_lifecycle(owner_user, tenant_client):
    """Backend lifecycle for a source record itself — there is no
    dedicated UI to edit or delete a source, so this is an invariant
    check: create → rename via PATCH → delete → gone from the list."""
    api = tenant_client(owner_user)

    created = api.post(
        API.SOURCES,
        json={"id": "src-crud-test", "name": TestData.SOURCE_NAME, "type": "document"},
    )
    expect_response(created, label="POST source").status_ok()
    sid = created.json()["id"]

    patched = api.patch(API.source(sid), json={"name": TestData.SOURCE_NAME_PATCHED})
    expect_response(patched, label="PATCH source").status_ok().json_eq("name", TestData.SOURCE_NAME_PATCHED)

    deleted = api.delete(API.source(sid))
    expect_response(deleted, label="DELETE source").status(204)

    listed = api.get(API.SOURCES)
    expect_response(listed, label="GET sources after delete").status_ok()
    assert not any(s["id"] == sid for s in listed.json()), \
        "deleted source still appears in GET /api/sources"
