"""Add-relative dedup — graph-aware suggestion предотвращает дубликаты родителей."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import person_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from helpers.tree.add_relative import add_sibling_without_auto_parents
from helpers.tree.tree_api import (
    demo_parents_of_self,
    find_person_by_name,
    people,
    relationships,
)
from models.person import PersonCreate
from pages.add_relative_modal import AddRelativeModal
from pages.profile_panel import ProfilePanel
from src.texts import AgeValidation, ErrMsg, FamilyGroups, TestData, t

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx
    from playwright.sync_api import Request, Route

    from fixtures.users import AuthUser


@allure.title("Подсказка родителя для сестры предотвращает дубликат")
def test_sibling_parent_suggestion_prevents_duplicate(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Привязка отца через suggestion предотвращает дубликат."""
    with step("подготовка: получить demo-родителей и запомнить count"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)
        demo_father_id = parents["m"]

        people_before = people(api)
        count_before = len(people_before)
        should.be_in(demo_father_id, {p["id"] for p in people_before}, ErrMsg.demo_father_not_in_seed)

    with step("действие: добавить сиблинга без auto-parent"):
        ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        add_sibling_without_auto_parents(
            owner_page,
            surname="Тестовая",
            given="Светлана",
            birth="15.06.1992",
            gender="f",
        )
        svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    with step("действие: открыть Светлану и привязать отца через suggestion"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, svetlana["id"])
        panel.click_add_parent()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

        modal.expect_suggestion_visible(demo_father_id)

        modal.click_suggestion(demo_father_id)
        modal.expect_linked_to(demo_father_id)
        modal.save_and_expect_response(f"**{routes.RELATIONSHIPS}**")
        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()

    with step("проверка: ровно один новый person, оба ребёнка на одном отце"):
        people_after = people(api)
        should.have_length(people_after, count_before + 1, ErrMsg.person_count_wrong)

        rels = relationships(api)
        father_edges = {r["person2_id"]: r for r in rels if r["type"] == "parent" and r["person1_id"] == demo_father_id}
        should.be_in(TestData.DEMO_PERSON_ID, father_edges, ErrMsg.parent_link_missing)
        should.be_in(svetlana["id"], father_edges, ErrMsg.parent_link_missing)
        should.be_false(
            any(p["id"].endswith("-2") for p in people_after),
            ErrMsg.duplicate_person_found,
        )


@allure.title("Подсказки родителей фильтруются по выбранному полу")
def test_suggestion_filters_by_gender_for_mother_relationship(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Фильтрация suggestion по полу: f показывает мать, m — отца."""
    with step("подготовка: добавить сиблинга без auto-parent"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)

        ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        add_sibling_without_auto_parents(owner_page, surname="Тестовая", given="Светлана", gender="f")
        svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    with step("действие: открыть Светлану и переключать пол"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, svetlana["id"])
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

    with step("проверка: gender=f показывает только мать, gender=m только отца"):
        modal.select_gender("f")
        expect(modal.suggestion_card_by_id(parents["f"]), ErrMsg.suggestion_not_visible).to_be_visible()
        expect(modal.suggestion_card_by_id(parents["m"]), ErrMsg.suggestion_count_wrong).to_have_count(0)

        modal.select_gender("m")
        expect(modal.suggestion_card_by_id(parents["m"]), ErrMsg.suggestion_not_visible).to_be_visible()
        expect(modal.suggestion_card_by_id(parents["f"]), ErrMsg.suggestion_count_wrong).to_have_count(0)


@allure.title("Подсказки отсутствуют у персоны без братьев и сестёр")
def test_no_suggestion_when_no_siblings(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Персона без siblings не получает suggestion — нечего предлагать."""
    with step("подготовка: создать изолированную персону без siblings"):
        api = tenant_client(owner_user)
        demo_parents_of_self(api)  # sanity: seed правильно собрался

        lonely = person_api.create_person(
            api,
            PersonCreate(
                id="lonely-test",
                name="Одинокий Тестовый",
                gender="m",
                birth="1980",
                branch="other",
            ),
        )
        lonely_id = lonely.id

    with step("действие: открыть профиль и нажать + родитель"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, lonely_id)
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

    with step("проверка: подсказки отсутствуют"):
        modal.expect_no_suggestions()


@allure.title("Подсказки пусты когда у сиблингов нет родителей")
def test_no_suggestion_when_siblings_have_no_parents(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Два siblings без parents → suggestion пуст при добавлении родителя."""
    with step("подготовка: создать двух сиблингов без родителей"):
        api = tenant_client(owner_user)

        person_api.create_person(
            api,
            PersonCreate(
                id="lone_a",
                name="Одинокий Альфа",
                gender="m",
                branch="other",
                status="confirmed",
            ),
        )
        person_api.create_person(
            api,
            PersonCreate(
                id="lone_b",
                name="Одинокий Бета",
                gender="m",
                branch="other",
                status="confirmed",
            ),
        )
        r_rel = api.post(
            routes.RELATIONSHIPS,
            json={
                "type": "sibling",
                "person1_id": "lone_a",
                "person2_id": "lone_b",
            },
        )
        expect_response(r_rel, label="create sibling rel").status_ok()

    with step("действие: открыть профиль и нажать + родитель"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, "lone_a")
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

    with step("проверка: подсказки отсутствуют"):
        modal.expect_no_suggestions()


@allure.title("Кнопка '+ родитель' скрыта при достижении лимита в 2 родителя")
def test_no_suggestion_when_max_parents_already(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Кнопка +parent скрыта при наличии 2 родителей (RELATIVE_LIMITS)."""
    with step("подготовка: проверить наличие двух demo-родителей"):
        api = tenant_client(owner_user)
        demo_parents_of_self(api)  # sanity

    with step("проверка: кнопка + родитель скрыта при 2 родителях"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        parents_add_btn = panel.add_relative_button(t(FamilyGroups.PARENTS))
        expect(parents_add_btn, ErrMsg.parent_button_should_be_hidden).to_have_count(0)


@allure.title("Игнорирование подсказки создаёт нового человека вручную")
def test_user_ignores_suggestion_creates_new_person(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Игнорирование suggestion создаёт нового person'а, не мерджит."""
    with step("подготовка: добавить сиблинга без auto-parent"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)
        demo_father_id = parents["m"]

        ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        add_sibling_without_auto_parents(owner_page, surname="Тестовая", given="Светлана", gender="f")
        svetlana = find_person_by_name(api, "Светлана", "Тестовая")
        count_before_add_father = len(people(api))

    with step("действие: игнорировать suggestion и создать нового родителя вручную"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, svetlana["id"])
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.expect_suggestion_visible(demo_father_id)

        modal.fill_fio(surname="Прадедов", given="Иннокентий", birth="01.01.1900")
        modal.select_gender("m")

        modal.save_and_expect_response(f"**{routes.PEOPLE}**")
        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()

    with step("проверка: новый person создан, demo-father не затронут"):
        people_after = people(api)
        should.have_length(people_after, count_before_add_father + 1, ErrMsg.person_count_wrong)
        rels = relationships(api)
        self_fathers = [
            r["person1_id"] for r in rels if r["type"] == "parent" and r["person2_id"] == TestData.DEMO_PERSON_ID
        ]
        should.be_in(demo_father_id, self_fathers, ErrMsg.father_not_linked)
        sv_father_rels = [r for r in rels if r["type"] == "parent" and r["person2_id"] == svetlana["id"]]
        should.have_length(sv_father_rels, 1, ErrMsg.relationship_count_wrong)
        new_father_id = sv_father_rels[0]["person1_id"]
        should.not_equal(new_father_id, demo_father_id, ErrMsg.new_father_must_differ)
        new_father = next(p for p in people_after if p["id"] == new_father_id)
        should.contain(new_father["name"], "Иннокентий", ErrMsg.canonical_name_wrong)


@allure.title("Клик по подсказке привязывает существующего, не создаёт нового")
def test_suggestion_click_does_not_create_new_person(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Клик suggestion не дёргает POST /api/people — только relationships."""
    with step("подготовка: добавить сиблинга и открыть модалку родителя"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)
        demo_father_id = parents["m"]

        ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        add_sibling_without_auto_parents(owner_page, surname="Тестовая", given="Светлана", gender="f")
        svetlana = find_person_by_name(api, "Светлана", "Тестовая")

        panel = ProfilePanel.navigate_to_fresh(owner_page, svetlana["id"])
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.expect_suggestion_visible(demo_father_id)

    with step("действие: кликнуть suggestion и сохранить"):
        posted_people: list[str] = []

        def _on_request(req: Request) -> None:
            if req.method == "POST" and routes.PEOPLE in req.url and routes.PEOPLE + "-" not in req.url:
                posted_people.append(req.url)

        owner_page.on("request", _on_request)
        try:
            modal.click_suggestion(demo_father_id)
            modal.expect_linked_to(demo_father_id)
            modal.save_and_expect_response(f"**{routes.RELATIONSHIPS}**")
            expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()
        finally:
            owner_page.remove_listener("request", _on_request)

    with step("проверка: POST /api/people не вызывался"):
        should.be_empty(posted_people, ErrMsg.people_post_not_expected)


@allure.title("Чекбокс 'Те же родители' привязывает обоих родителей к сиблингу")
def test_existing_sibling_auto_parent_checkbox_still_works(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Чекбокс auto-parent привязывает обоих demo-родителей к новому сиблингу."""
    with step("подготовка: получить demo-родителей"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)

    with step("действие: добавить сиблинга с чекбоксом 'Те же родители'"):
        panel = ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        panel.click_add_sibling()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

        expect(modal.share_parents_input, ErrMsg.checkbox_state_wrong).to_be_checked()

        modal.fill_fio(surname="Тестовая", given="Брат", birth="01.01.1985")
        modal.select_gender("m")

        modal.save_and_expect_response(f"**{routes.PEOPLE}**")
        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()

    with step("проверка: новый сиблинг привязан к обоим demo-родителям"):
        brat = find_person_by_name(api, "Брат", "Тестовая")
        rels = relationships(api)
        brat_parents = {r["person1_id"] for r in rels if r["type"] == "parent" and r["person2_id"] == brat["id"]}
        should.be_in(parents["m"], brat_parents, ErrMsg.father_not_linked)
        should.be_in(parents["f"], brat_parents, ErrMsg.mother_not_linked)


@allure.title("Ошибка 422 при привязке подсказки оставляет модалку открытой")
def test_suggestion_click_shows_error_on_backend_422(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Бэк 422 на suggestion → модалка открыта, error visible, граф не меняется."""
    with step("подготовка: добавить сиблинга и открыть модалку родителя"):
        api = tenant_client(owner_user)
        parents = demo_parents_of_self(api)
        demo_father_id = parents["m"]

        ProfilePanel.navigate_to_fresh(owner_page, TestData.DEMO_PERSON_ID)
        add_sibling_without_auto_parents(owner_page, surname="Тестовая", given="Светлана", gender="f")
        svetlana = find_person_by_name(api, "Светлана", "Тестовая")

        rels_before = relationships(api)

        panel = ProfilePanel.navigate_to_fresh(owner_page, svetlana["id"])
        panel.click_add_parent()
        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.expect_suggestion_visible(demo_father_id)

    with step("действие: перехватить 422 и кликнуть suggestion"):

        def _block_with_422(route: Route) -> None:
            if route.request.method == "POST":
                route.fulfill(
                    status=422,
                    content_type="application/json",
                    body='{"detail":"Возраст родителя должен превышать возраст ребёнка минимум на 14 лет"}',
                )
            else:
                route.continue_()

        owner_page.route(f"**{routes.RELATIONSHIPS}*", _block_with_422)
        try:
            modal.click_suggestion(demo_father_id)
            modal.expect_linked_to(demo_father_id)
            modal.save()
            expect(modal.overlay, ErrMsg.modal_not_visible).to_be_visible()
            expect(modal.error, ErrMsg.validation_error_wrong).to_be_visible()
            expect(modal.error, ErrMsg.validation_error_wrong).to_contain_text(t(AgeValidation.PARENT_AGE_KEYWORD))
        finally:
            owner_page.unroute(f"**{routes.RELATIONSHIPS}*")

    with step("проверка: граф не изменился"):
        rels_after = relationships(api)
        should.have_length(rels_after, len(rels_before), ErrMsg.relationship_count_wrong)
