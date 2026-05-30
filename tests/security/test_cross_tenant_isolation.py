"""Cross-tenant isolation invariants."""

from __future__ import annotations

import concurrent.futures as cf
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser
from api.person_api import get_tree
from assertions.base import should
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg


@allure.title("Изоляция: персона тенанта A не видна тенанту B")
def test_person_created_in_tenant_a_not_visible_in_tenant_b(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Тенант A создаёт person, тенант B не видит его в /api/tree."""
    with step("подготовка: создать два независимых тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()
        should.not_equal(user_a.slug, user_b.slug, ErrMsg.tenants_must_differ)

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: тенант A создаёт уникального person'а"):
        created = (
            expect_response(
                api_a.post(
                    routes.PEOPLE,
                    json={
                        "name": "Тенант-А Уникум",
                        "surname": "Уникум",
                        "given_name": "Тенант-А",
                        "gender": "m",
                    },
                ),
                label="create person A",
            )
            .status_ok()
            .data
        )
        should.be_true(created["id"], ErrMsg.person_must_have_id)

    with step("проверка: тенант B не видит person'а тенанта A"):
        tree_b = get_tree(api_b)
        b_person_ids = {p.id for p in tree_b.people}
        b_names = {p.name for p in tree_b.people}
        should.not_contain(str(b_person_ids), created["id"], ErrMsg.person_id_leaked)
        should.not_contain(str(b_names), "Тенант-А Уникум", ErrMsg.person_name_leaked)


@allure.title("Изоляция: чтение чужой персоны по ID возвращает 404")
def test_tenant_b_cannot_read_tenant_a_person_by_id(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Прямой GET /api/people/{id} с чужим id возвращает 404."""
    with step("подготовка: создать два тенанта и person в тенанте A"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        created = (
            expect_response(
                api_a.post(routes.PEOPLE, json={"name": "Чужой Person", "gender": "m"}),
                label="create person A",
            )
            .status_ok()
            .data
        )
        should.be_true(created["id"], ErrMsg.person_must_have_id)

    with step("проверка: тенант B получает 404 при чтении чужого person"):
        r = api_b.get(routes.person(created["id"]))
        expect_response(r, label="cross-tenant read person").status(HTTPStatus.NOT_FOUND)


@allure.title("Изоляция: редактирование чужой персоны возвращает 404")
def test_tenant_b_cannot_patch_tenant_a_person(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """PATCH чужого person возвращает 404."""
    with step("подготовка: создать два тенанта и person в тенанте A"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        created = (
            expect_response(
                api_a.post(routes.PEOPLE, json={"name": "Чужой Edit", "gender": "m"}),
                label="create person A",
            )
            .status_ok()
            .data
        )

    with step("проверка: тенант B получает 404 при PATCH чужого person"):
        r = api_b.patch(routes.person(created["id"]), json={"summary": "MUTATED by B"})
        expect_response(r, label="cross-tenant write person").status(HTTPStatus.NOT_FOUND)


@allure.title("Изоляция: одинаковый display_slug допустим в разных тенантах")
def test_same_display_slug_allowed_across_tenants(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Tenant A и B могут иметь person с одинаковым display_slug без коллизии."""
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: создать person с одинаковым slug в обоих тенантах"):
        r_a = api_a.post(
            routes.PEOPLE,
            json={"name": "A Иван", "display_slug": "ivan-ivanov", "gender": "m"},
        )
        expect_response(r_a, label="create person A with slug").status(HTTPStatus.CREATED)
        r_b = api_b.post(
            routes.PEOPLE,
            json={"name": "B Иван", "display_slug": "ivan-ivanov", "gender": "m"},
        )
        expect_response(r_b, label="cross-tenant slug reuse").status(HTTPStatus.CREATED)

    with step("проверка: UUID'ы разные, коллизии нет"):
        data_a = expect_response(r_a, label="person A slug").status_ok().data
        data_b = expect_response(r_b, label="person B slug").status_ok().data
        should.not_equal(data_a["id"], data_b["id"], ErrMsg.slug_collision)


@allure.title("Изоляция: одинаковые ФИО получают разные tenant_slug")
def test_tenant_signup_with_same_display_name_gets_different_slugs(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Два signup с одинаковым full_name получают разные tenant_slug."""
    with step("действие: два signup с одинаковым full_name"):
        user_a = signup_via_api(full_name="Семья Ивановых")
        user_b = signup_via_api(full_name="Семья Ивановых")

    with step("проверка: tenant_slug различаются"):
        should.not_equal(user_a.slug, user_b.slug, ErrMsg.slug_collision)


@allure.title("Изоляция: GEDCOM-экспорт содержит только свои данные")
def test_gedcom_export_returns_only_own_tenant_data(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Tenant A экспортирует GEDCOM — файл содержит только его данные."""
    with step("подготовка: создать два тенанта с уникальными person'ами"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        api_a.post(routes.PEOPLE, json={"name": "ExportA Тестов", "gender": "m"})
        api_b.post(routes.PEOPLE, json={"name": "ExportB Чужой", "gender": "m"})

    with step("действие: тенант A экспортирует GEDCOM"):
        ged = api_a.get(routes.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long).text

    with step("проверка: экспорт содержит только данные тенанта A"):
        should.contain(ged, "ExportA", ErrMsg.gedcom_missing_own_data)
        should.not_contain(ged, "ExportB", ErrMsg.gedcom_leaked_foreign_data)


@allure.title("Изоляция: GEDCOM-импорт не затрагивает чужой тенант")
def test_gedcom_import_creates_persons_only_in_uploading_tenant(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Tenant A импортирует .ged, дерево tenant B не меняется."""
    with step("подготовка: создать два тенанта, запомнить размер дерева B"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)
        b_count_before = len(get_tree(api_b).people)

    with step("действие: тенант A импортирует GEDCOM-файл"):
        ged = (
            "0 HEAD\n1 SOUR Cross-Tenant-Test\n1 CHAR UTF-8\n0 @I1@ INDI\n1 NAME ImportA /Уникум/\n1 SEX M\n0 TRLR\n"
        ).encode()

        r = api_a.post(
            routes.ADMIN_IMPORT_GEDCOM,
            files={"file": ("isolation.ged", ged, "application/octet-stream")},
            timeout=TIMEOUTS.api_long,
        )
        # Hard pin: import endpoint должен принимать auth_v2 owner cookie (200).
        # Любой другой статус — regression auth_v2-bridge → fail loud, не skip.
        preview = (
            expect_response(
                r,
                label="GEDCOM import preview auth_v2",
            )
            .status(HTTPStatus.OK)
            .data
        )
        confirm = {k: preview.get(k, []) for k in ("people", "relationships", "sources")}
        api_a.post(routes.ADMIN_IMPORT_GEDCOM_CONFIRM, json=confirm)

    with step("проверка: дерево тенанта B не изменилось"):
        b_count_after = len(get_tree(api_b).people)
        should.be_equal(b_count_after, b_count_before, ErrMsg.tree_changed_after_import)


@allure.title("Изоляция: параллельные записи двух тенантов не пересекаются")
def test_concurrent_creates_in_two_tenants_dont_interfere(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Параллельные create в двух tenant'ах не создают cross-effects."""
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()

    with step("действие: параллельно создать по 5 person в каждом тенанте"):

        def _create_batch(user: AuthUser, label: str) -> None:
            api = tenant_client(user)
            for i in range(5):
                api.post(
                    routes.PEOPLE,
                    json={"name": f"{label}-Person-{i}", "gender": "m"},
                ).raise_for_status()

        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            f_a = ex.submit(_create_batch, user_a, "Concurr-A")
            f_b = ex.submit(_create_batch, user_b, "Concurr-B")
            f_a.result()
            f_b.result()

    with step("проверка: каждый тенант видит только свои записи"):
        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)
        a_names = {p.name for p in get_tree(api_a).people}
        b_names = {p.name for p in get_tree(api_b).people}

        for i in range(5):
            should.be_in(f"Concurr-A-Person-{i}", a_names, ErrMsg.own_person_missing)
            should.not_contain(str(a_names), f"Concurr-B-Person-{i}", ErrMsg.foreign_person_visible)
        for i in range(5):
            should.be_in(f"Concurr-B-Person-{i}", b_names, ErrMsg.own_person_missing)
            should.not_contain(str(b_names), f"Concurr-A-Person-{i}", ErrMsg.foreign_person_visible)
