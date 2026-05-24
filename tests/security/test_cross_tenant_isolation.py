"""Cross-tenant isolation invariants.

Multi-tenant SQLite — большая поверхность для багов: тенант видит чужие
данные, slug-collision при одинаковых ФИО, parallel signup race, cookie/
session leak.

Эти тесты проверяют что **изоляция реально работает**, а не предполагается
от architecture. Каждый тест создаёт два независимых tenant'а и
проверяет один граничный сценарий.

Стиль: API-only (без UI) — быстро и стабильно. UI-сценарии — отдельные
тесты в `tests/ui/`.
"""

from __future__ import annotations

import concurrent.futures as cf

import allure

from tests._core.api_paths import API
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS

# ─────────────────────────────────────────────────────────────────────────
# Data isolation
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Изоляция: персона тенанта A не видна тенанту B")
def test_person_created_in_tenant_a_not_visible_in_tenant_b(
    signup_via_api, tenant_client
):
    """Тенант A создаёт person → тенант B не видит его в /api/tree
    (главный изоляционный invariant)."""
    with step("подготовка: создать два независимых тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()
        assert user_a.slug != user_b.slug, "fixture sanity: tenants must differ"

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: тенант A создаёт уникального person'а"):
        created = api_a.post(
            API.PEOPLE,
            json={
                "name": "Тенант-А Уникум",
                "surname": "Уникум",
                "given_name": "Тенант-А",
                "gender": "m",
            },
        ).json()
        assert created["id"], "created person must have an id"

    with step("проверка: тенант B не видит person'а тенанта A"):
        tree_b = api_b.get(API.TREE).json()
        b_person_ids = {p["id"] for p in tree_b["people"]}
        b_names = {p["name"] for p in tree_b["people"]}
        assert created["id"] not in b_person_ids, (
            "LEAK: tenant_a's person id seen in tenant_b tree"
        )
        assert "Тенант-А Уникум" not in b_names, (
            f"LEAK: tenant_a's person name seen in tenant_b tree: {b_names}"
        )


@allure.title("Изоляция: чтение чужой персоны по ID возвращает 404")
def test_tenant_b_cannot_read_tenant_a_person_by_id(
    signup_via_api, tenant_client
):
    """Прямой GET /api/people/{id} с чужим id → 404 (per-tenant scope hides)."""
    with step("подготовка: создать два тенанта и person в тенанте A"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        created = api_a.post(
            API.PEOPLE, json={"name": "Чужой Person", "gender": "m"}
        ).json()
        assert created["id"], "created person must have an id"

    with step("проверка: тенант B получает 404 при чтении чужого person"):
        r = api_b.get(API.person(created["id"]))
        expect_response(r, label="cross-tenant read person").status(404)


@allure.title("Изоляция: редактирование чужой персоны возвращает 404")
def test_tenant_b_cannot_patch_tenant_a_person(signup_via_api, tenant_client):
    """Write-leak проверка: PATCH чужого person → 404 (per-tenant scope hides)."""
    with step("подготовка: создать два тенанта и person в тенанте A"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        created = api_a.post(API.PEOPLE, json={"name": "Чужой Edit", "gender": "m"}).json()

    with step("проверка: тенант B получает 404 при PATCH чужого person"):
        r = api_b.patch(API.person(created["id"]), json={"summary": "MUTATED by B"})
        expect_response(r, label="cross-tenant write person").status(404)


# ─────────────────────────────────────────────────────────────────────────
# Slug & UUID independence
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Изоляция: одинаковый display_slug допустим в разных тенантах")
def test_same_display_slug_allowed_across_tenants(signup_via_api, tenant_client):
    """display_slug — per-tenant, не global. Tenant A и B могут оба иметь
    person с `display_slug='ivan-ivanov'` — без коллизии."""
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

    with step("действие: создать person с одинаковым slug в обоих тенантах"):
        r_a = api_a.post(
            API.PEOPLE,
            json={"name": "A Иван", "display_slug": "ivan-ivanov", "gender": "m"},
        )
        expect_response(r_a, label="create person A with slug").status(201)
        r_b = api_b.post(
            API.PEOPLE,
            json={"name": "B Иван", "display_slug": "ivan-ivanov", "gender": "m"},
        )
        expect_response(r_b, label="cross-tenant slug reuse").status(201)

    with step("проверка: UUID'ы разные, коллизии нет"):
        assert r_a.json()["id"] != r_b.json()["id"], \
            "same display_slug must resolve to different people across tenants"


@allure.title("Изоляция: одинаковые ФИО получают разные tenant_slug")
def test_tenant_signup_with_same_display_name_gets_different_slugs(
    signup_via_api, tenant_client
):
    """Два signup'а с одинаковым `full_name` → разные tenant_slug
    (auto-suffix или random). Без этого — overlap данных."""
    with step("действие: два signup с одинаковым full_name"):
        user_a = signup_via_api(full_name="Семья Ивановых")
        user_b = signup_via_api(full_name="Семья Ивановых")

    with step("проверка: tenant_slug различаются"):
        assert user_a.slug != user_b.slug, (
            f"tenants got same slug {user_a.slug!r} — collision risk"
        )


# ─────────────────────────────────────────────────────────────────────────
# GEDCOM isolation
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Изоляция: GEDCOM-экспорт содержит только свои данные")
def test_gedcom_export_returns_only_own_tenant_data(signup_via_api, tenant_client):
    """Tenant A экспортирует GEDCOM → файл содержит только его данные."""
    with step("подготовка: создать два тенанта с уникальными person'ами"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        api_a.post(API.PEOPLE, json={"name": "ExportA Тестов", "gender": "m"})
        api_b.post(API.PEOPLE, json={"name": "ExportB Чужой", "gender": "m"})

    with step("действие: тенант A экспортирует GEDCOM"):
        ged = api_a.get(API.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long).text

    with step("проверка: экспорт содержит только данные тенанта A"):
        assert "ExportA" in ged, \
            f"GEDCOM export must contain own tenant's data: {ged[:100]!r}"
        assert "ExportB" not in ged, (
            "LEAK: tenant_a GEDCOM export contains tenant_b person name"
        )


@allure.title("Изоляция: GEDCOM-импорт не затрагивает чужой тенант")
def test_gedcom_import_creates_persons_only_in_uploading_tenant(
    signup_via_api, tenant_client
):
    """Tenant A импортирует .ged → tenant B свой tree не меняется."""
    with step("подготовка: создать два тенанта, запомнить размер дерева B"):
        user_a = signup_via_api()
        user_b = signup_via_api()

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)
        b_count_before = len(api_b.get(API.TREE).json()["people"])

    with step("действие: тенант A импортирует GEDCOM-файл"):
        ged = (
            "0 HEAD\n"
            "1 SOUR Cross-Tenant-Test\n"
            "1 CHAR UTF-8\n"
            "0 @I1@ INDI\n"
            "1 NAME ImportA /Уникум/\n"
            "1 SEX M\n"
            "0 TRLR\n"
        ).encode()

        r = api_a.post(
            API.ADMIN_IMPORT_GEDCOM,
            files={"file": ("isolation.ged", ged, "application/octet-stream")},
            timeout=TIMEOUTS.api_long,
        )
        # Hard pin: import endpoint должен принимать auth_v2 owner cookie (200).
        # Любой другой статус — regression auth_v2-bridge → fail loud, не skip.
        expect_response(r, label="GEDCOM import preview auth_v2").status(200)
        preview = r.json()
        confirm = {k: preview.get(k, []) for k in ("people", "relationships", "sources")}
        api_a.post(API.ADMIN_IMPORT_GEDCOM_CONFIRM, json=confirm)

    with step("проверка: дерево тенанта B не изменилось"):
        b_count_after = len(api_b.get(API.TREE).json()["people"])
        assert b_count_after == b_count_before, (
            f"LEAK: tenant_b's tree changed after tenant_a's GEDCOM import "
            f"(before={b_count_before}, after={b_count_after})"
        )


# ─────────────────────────────────────────────────────────────────────────
# Concurrent operations
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Изоляция: параллельные записи двух тенантов не пересекаются")
def test_concurrent_creates_in_two_tenants_dont_interfere(
    signup_via_api, tenant_client
):
    """Параллельные create-операции в двух tenant'ах — никаких cross-effects
    (без потери записей, без чужих записей)."""
    with step("подготовка: создать два тенанта"):
        user_a = signup_via_api()
        user_b = signup_via_api()

    with step("действие: параллельно создать по 5 person в каждом тенанте"):
        def _create_batch(user, label: str) -> None:
            api = tenant_client(user)
            for i in range(5):
                api.post(
                    API.PEOPLE,
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
        a_names = {p["name"] for p in api_a.get(API.TREE).json()["people"]}
        b_names = {p["name"] for p in api_b.get(API.TREE).json()["people"]}

        # A видит только свои concurr-A-* persons
        for i in range(5):
            assert f"Concurr-A-Person-{i}" in a_names, \
                f"tenant_a missing own person Concurr-A-Person-{i}: {a_names}"
            assert f"Concurr-B-Person-{i}" not in a_names, (
                f"LEAK: tenant_a sees tenant_b person Concurr-B-Person-{i}"
            )
        # B видит только свои concurr-B-* persons
        for i in range(5):
            assert f"Concurr-B-Person-{i}" in b_names, \
                f"tenant_b missing own person Concurr-B-Person-{i}: {b_names}"
            assert f"Concurr-A-Person-{i}" not in b_names, \
                f"LEAK: tenant_b sees tenant_a person Concurr-A-Person-{i}"
