"""Domain invariants — INV-DOMAIN-001..005, INV-DATE-001, INV-CASCADE-001,
INV-TXN-001, INV-DATA-001.

Backend хранит persons + relationships. У этих сущностей есть
**доменные инварианты**, которые backend обязан валидировать
независимо от frontend (frontend может скрыть кнопку, но прямой
PATCH/POST через API должен отбиваться).

Все тесты используют `tenant_client(user)` factory — `httpx.Client`
pre-wired с base_url + cookies + slug header. Никаких raw httpx-
вызовов из тестов.
"""

from __future__ import annotations

import allure

from tests._core.api_paths import API
from tests._core.constants import unique_email
from tests._core.messages import TestData
from tests._core.response import expect_response
from tests._core.step import step
from tests._data.payloads.tree import parent_rel
from tests._models.person import PersonCreate
from tests.helpers.api import person_api, relationship_api

# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-001 / INV-DOMAIN-004 / INV-DATE-001 — date validation
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Бэкенд отклоняет дату смерти раньше даты рождения")
def test_patch_person_death_before_birth_is_422(owner_user, tenant_client):
    """INV-DOMAIN-001: backend rejects death year < birth year.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        API.person(TestData.DEMO_PERSON_ID),
        json={"birth": "1920", "death": "1900"},
    )
    expect_response(r, label="death before birth").status(400, 422)


@allure.title("Бэкенд отклоняет рождение родителя позже ребёнка")
def test_patch_parent_birth_after_child_is_422(signup_via_api, tenant_client):
    """INV-DOMAIN-004: parent.birth must precede child.birth (>= ~14y).

    Was xfail (partial fix until PATCH-handler validation). Closed by
    upstream batch-6/7. Now regular regression.
    """
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
        r = api.patch(API.person("dom004-parent"), json={"birth": "2000"})
        expect_response(r, label="parent birth after child").status(400, 422)


@allure.title("Бэкенд отклоняет непарсируемую дату рождения")
def test_patch_person_garbage_birth_is_422(owner_user, tenant_client):
    """INV-DATE-001: birth='foobar' (non-parseable) must be rejected.

    Was xfail until upstream batch-6/7 (date format validator).
    Now regular regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        API.person(TestData.DEMO_PERSON_ID),
        json={"birth": "foobar"},
    )
    expect_response(r, label="garbage birth value").status(400, 422)


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-002 — >2 parents
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Бэкенд отклоняет третьего родителя у ребёнка")
def test_third_parent_relationship_is_rejected(signup_via_api, tenant_client):
    """INV-DOMAIN-002: backend should reject >2 parents per child.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
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
        r = api.post(API.RELATIONSHIPS, json=parent_rel("dom002-p3", "dom002-child"))
        expect_response(r, label="3rd parent").status(400, 409, 422)


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-003 — cycle in parent graph
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Бэкенд отклоняет цикл в графе родительских связей")
def test_parent_cycle_is_rejected(signup_via_api, tenant_client):
    """INV-DOMAIN-003: A parent of B + B parent of A → backend rejects 2nd.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
    with step("подготовка: создание A, B и связи A→B"):
        user = signup_via_api(email=unique_email("dom003"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(id="dom003-a", name="Цикл-A"))
        person_api.create_person(api, PersonCreate(id="dom003-b", name="Цикл-B"))

        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="dom003-a", person2_id="dom003-b",
        )

    with step("проверка: обратная связь B→A отклонена"):
        r2 = api.post(API.RELATIONSHIPS, json=parent_rel("dom003-b", "dom003-a"))
        expect_response(r2, label="parent cycle B->A->B").status(400, 409, 422)


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-005 — subject не может уйти на branch=demo
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Корневой субъект нельзя перевести в ветку demo")
def test_subject_cannot_be_demoted_to_demo_branch(owner_user, tenant_client):
    """INV-DOMAIN-005: root subject can't have branch=demo.

    Was xfail until upstream batch-6/7. Now regular regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(API.person(TestData.DEMO_PERSON_ID), json={"branch": "demo"})
    expect_response(r, label="subject demoted to demo").status(400, 409, 422)


# ─────────────────────────────────────────────────────────────────────────
# INV-CASCADE-001 — DELETE non-root → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Удаление персоны со связями не вызывает ошибку 500")
def test_delete_non_root_person_with_relationship_does_not_500(
    signup_via_api, tenant_client,
):
    """INV-CASCADE-001: DELETE non-root person *с relationships* must
    not crash with 500. Изолированный person удалялся и без cascade-
    handling — реальный баг проявлялся когда есть FK.

    Was xfail at Run security 28.04 night. Closed by upstream batch-2.
    """
    with step("подготовка: создание ребёнка, родителя и связи"):
        user = signup_via_api(email=unique_email("cascade"))
        api = tenant_client(user)

        person_api.create_person(api, PersonCreate(id="cascade-child", name="Ребёнок", branch="subject"))
        person_api.create_person(api, PersonCreate(id="cascade-parent", name="Родитель"))
        relationship_api.create_relationship(
            api, rel_type="parent", person1_id="cascade-parent", person2_id="cascade-child",
        )

    with step("проверка: DELETE не вызывает 500"):
        r = api.delete(API.person("cascade-parent"))
        assert r.status_code < 500, (
            f"DELETE /api/people/cascade-parent crashed {r.status_code} -- "
            f"cascade not handled. Body: {r.text[:300]}"
        )


# ─────────────────────────────────────────────────────────────────────────
# INV-TXN-001 — orphan FK → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Связь с несуществующей персоной возвращает 404, не 500")
def test_relationship_with_orphan_person_id_returns_404_not_500(
    signup_via_api, tenant_client,
):
    """INV-TXN-001: POST relationship referencing non-existent person
    must return 404 (or 422), never 500.

    Was xfail until upstream commit `4007a3a`. Now regression.
    """
    with step("подготовка: создание реальной персоны"):
        user = signup_via_api(email=unique_email("txn001"))
        api = tenant_client(user)
        person_api.create_person(api, PersonCreate(id="txn001-real", name="Реальный"))

    with step("проверка: связь с несуществующим ID возвращает 400/404/422"):
        r = api.post(
            API.RELATIONSHIPS,
            json={"type": "parent", "person1_id": "txn001-real", "person2_id": "NONEXIST-ORPHAN-ID"},
        )
        expect_response(r, label="orphan FK relationship").status(400, 404, 422)


# ─────────────────────────────────────────────────────────────────────────
# INV-DATA-001 — нет upper bound на размер surname/notes
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Бэкенд отклоняет слишком длинные заметки (50 КБ)")
def test_patch_person_huge_notes_is_rejected(owner_user, tenant_client):
    """INV-DATA-001: notes > reasonable bound (e.g. 10K) must be rejected.

    Was xfail until upstream commit `187bedb`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        API.person(TestData.DEMO_PERSON_ID),
        json={"notes": "X" * (50 * 1024)},  # 50 KB
    )
    expect_response(r, label="50KB notes rejected").status(400, 413, 422)


@allure.title("Бэкенд отклоняет слишком длинную фамилию (5000 символов)")
def test_patch_person_huge_surname_is_rejected(owner_user, tenant_client):
    """INV-DATA-001: surname > reasonable bound (e.g. 100) must be rejected.

    Was xfail until upstream commit `187bedb`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        API.person(TestData.DEMO_PERSON_ID),
        json={"surname": "А" * 5_000},
    )
    expect_response(r, label="5K-char surname rejected").status(400, 413, 422)
