"""Domain invariants — валидация бэкендом persons + relationships."""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import person_api, relationship_api, routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from models.person import PersonCreate
from src.texts import ErrMsg, TestData
from test_data.payloads.tree import parent_rel


@allure.title("Бэкенд отклоняет дату смерти раньше даты рождения")
def test_patch_person_death_before_birth_is_422(owner_user, tenant_client) -> None:
    """INV-DOMAIN-001: death year < birth year отклоняется."""
    api = tenant_client(owner_user)
    r = api.patch(
        routes.person(TestData.DEMO_PERSON_ID),
        json={"birth": "1920", "death": "1900"},
    )
    expect_response(r, label="death before birth").status(HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)


@allure.title("Бэкенд отклоняет рождение родителя позже ребёнка")
def test_patch_parent_birth_after_child_is_422(signup_via_api, tenant_client) -> None:
    """INV-DOMAIN-004: рождение родителя должно предшествовать ребёнку."""
    with step("подготовка: создание ребёнка (1985) и родителя (1960) со связью"):
        user = signup_via_api(email=unique_email("dom004"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(
            id="dom004-child", name="Ребёнок", branch="subject", birth="1985",
        ))
        person_api.create_person(api, PersonCreate(
            id="dom004-parent", name="Родитель", birth="1960",
        ))
        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="dom004-parent", person2_id="dom004-child",
        )

    with step("проверка: PATCH birth=2000 отклонён (400/422)"):
        r = api.patch(routes.person("dom004-parent"), json={"birth": "2000"})
        expect_response(r, label="parent birth after child").status(
            HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY,
        )


@allure.title("Бэкенд отклоняет непарсируемую дату рождения")
def test_patch_person_garbage_birth_is_422(owner_user, tenant_client) -> None:
    """INV-DATE-001: непарсируемая дата рождения отклоняется."""
    api = tenant_client(owner_user)
    r = api.patch(
        routes.person(TestData.DEMO_PERSON_ID),
        json={"birth": "foobar"},
    )
    expect_response(r, label="garbage birth value").status(HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)



@allure.title("Бэкенд отклоняет третьего родителя у ребёнка")
def test_third_parent_relationship_is_rejected(signup_via_api, tenant_client) -> None:
    """INV-DOMAIN-002: >2 родителей у ребёнка отклоняется."""
    with step("подготовка: создание ребёнка и трёх родителей, привязка двух"):
        user = signup_via_api(email=unique_email("dom002"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(id="dom002-child", name="Ребёнок", branch="subject"))
        for pid, pname in (("dom002-p1", "Родитель-1"), ("dom002-p2", "Родитель-2"), ("dom002-p3", "Родитель-3")):
            person_api.create_person(api, PersonCreate(id=pid, name=pname))

        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="dom002-p1", person2_id="dom002-child",
        )
        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="dom002-p2", person2_id="dom002-child",
        )

    with step("проверка: третий родитель отклонён"):
        r = api.post(routes.RELATIONSHIPS, json=parent_rel("dom002-p3", "dom002-child"))
        expect_response(r, label="3rd parent").status(
            HTTPStatus.BAD_REQUEST, HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY,
        )



@allure.title("Бэкенд отклоняет цикл в графе родительских связей")
def test_parent_cycle_is_rejected(signup_via_api, tenant_client) -> None:
    """INV-DOMAIN-003: цикл A→B→A в parent graph отклоняется."""
    with step("подготовка: создание A, B и связи A→B"):
        user = signup_via_api(email=unique_email("dom003"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(id="dom003-a", name="Цикл-A"))
        person_api.create_person(api, PersonCreate(id="dom003-b", name="Цикл-B"))

        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="dom003-a", person2_id="dom003-b",
        )

    with step("проверка: обратная связь B→A отклонена"):
        r2 = api.post(routes.RELATIONSHIPS, json=parent_rel("dom003-b", "dom003-a"))
        expect_response(r2, label="parent cycle B->A->B").status(
            HTTPStatus.BAD_REQUEST, HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY,
        )



@allure.title("Корневой субъект нельзя перевести в ветку demo")
def test_subject_cannot_be_demoted_to_demo_branch(owner_user, tenant_client) -> None:
    """INV-DOMAIN-005: root subject нельзя перевести в branch=demo."""
    api = tenant_client(owner_user)
    r = api.patch(routes.person(TestData.DEMO_PERSON_ID), json={"branch": "demo"})
    expect_response(r, label="subject demoted to demo").status(
        HTTPStatus.BAD_REQUEST, HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY,
    )



@allure.title("Удаление персоны со связями не вызывает ошибку 500")
def test_delete_non_root_person_with_relationship_does_not_500(
    signup_via_api, tenant_client,
) -> None:
    """INV-CASCADE-001: DELETE персоны со связями не должен возвращать 500."""
    with step("подготовка: создание ребёнка, родителя и связи"):
        user = signup_via_api(email=unique_email("cascade"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(id="cascade-child", name="Ребёнок", branch="subject"))
        person_api.create_person(api, PersonCreate(id="cascade-parent", name="Родитель"))
        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="cascade-parent", person2_id="cascade-child",
        )

    with step("проверка: DELETE не вызывает 500"):
        r = api.delete(routes.person("cascade-parent"))
        should.less(r.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, ErrMsg.delete_500_crash)



@allure.title("Связь с несуществующей персоной возвращает 404, не 500")
def test_relationship_with_orphan_person_id_returns_404_not_500(
    signup_via_api, tenant_client,
) -> None:
    """INV-TXN-001: связь с несуществующим person → 4xx, не 500."""
    with step("подготовка: создание реальной персоны"):
        user = signup_via_api(email=unique_email("txn001"))
        api = tenant_client(user)
        person_api.create_person(api, PersonCreate(id="txn001-real", name="Реальный"))

    with step("проверка: связь с несуществующим ID возвращает 400/404/422"):
        r = api.post(
            routes.RELATIONSHIPS,
            json={"type": "parent", "person1_id": "txn001-real", "person2_id": "NONEXIST-ORPHAN-ID"},
        )
        expect_response(r, label="orphan FK relationship").status(
            HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY,
        )



@allure.title("Бэкенд отклоняет слишком длинные заметки (50 КБ)")
def test_patch_person_huge_notes_is_rejected(owner_user, tenant_client) -> None:
    """INV-DATA-001: notes > 50KB отклоняются."""
    api = tenant_client(owner_user)
    r = api.patch(
        routes.person(TestData.DEMO_PERSON_ID),
        json={"notes": "X" * (50 * 1024)},  # 50 KB
    )
    expect_response(r, label="50KB notes rejected").status(
        HTTPStatus.BAD_REQUEST, HTTPStatus.CONTENT_TOO_LARGE, HTTPStatus.UNPROCESSABLE_ENTITY,
    )


@allure.title("Бэкенд отклоняет слишком длинную фамилию (5000 символов)")
def test_patch_person_huge_surname_is_rejected(owner_user, tenant_client) -> None:
    """INV-DATA-001: surname > 5000 символов отклоняется."""
    api = tenant_client(owner_user)
    r = api.patch(
        routes.person(TestData.DEMO_PERSON_ID),
        json={"surname": "А" * 5_000},
    )
    expect_response(r, label="5K-char surname rejected").status(
        HTTPStatus.BAD_REQUEST, HTTPStatus.CONTENT_TOO_LARGE, HTTPStatus.UNPROCESSABLE_ENTITY,
    )
