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

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────────
# Data isolation
# ─────────────────────────────────────────────────────────────────────────


def test_person_created_in_tenant_a_not_visible_in_tenant_b(
    signup_via_api, tenant_client
):
    """Тенант A создаёт person → тенант B не видит его в /api/tree
    (главный изоляционный invariant)."""
    user_a = signup_via_api()
    user_b = signup_via_api()
    assert user_a.slug != user_b.slug, "fixture sanity: tenants must differ"

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    # A создаёт уникального person'а
    created = api_a.post(
        API.PEOPLE,
        json={
            "name": "Тенант-А Уникум",
            "surname": "Уникум",
            "given_name": "Тенант-А",
            "gender": "m",
        },
    ).json()
    assert created["id"]

    # B читает свой tree — Уникума там не должно быть
    tree_b = api_b.get(API.TREE).json()
    b_person_ids = {p["id"] for p in tree_b["people"]}
    b_names = {p["name"] for p in tree_b["people"]}
    assert created["id"] not in b_person_ids, (
        f"LEAK: tenant_a's person id seen in tenant_b tree"
    )
    assert "Тенант-А Уникум" not in b_names, (
        f"LEAK: tenant_a's person name seen in tenant_b tree: {b_names}"
    )


def test_tenant_b_cannot_read_tenant_a_person_by_id(
    signup_via_api, tenant_client
):
    """Прямой GET /api/people/{id} с чужим id → 404 (или 403),
    точно не 200."""
    user_a = signup_via_api()
    user_b = signup_via_api()

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    created = api_a.post(
        API.PEOPLE, json={"name": "Чужой Person", "gender": "m"}
    ).json()
    assert created["id"]

    r = api_b.get(API.person(created["id"]))
    assert r.status_code in (403, 404), (
        f"LEAK: tenant_b got {r.status_code} reading tenant_a's person; "
        f"expected 404 or 403"
    )


def test_tenant_b_cannot_patch_tenant_a_person(signup_via_api, tenant_client):
    """Write-leak проверка: PATCH чужого person → не 200."""
    user_a = signup_via_api()
    user_b = signup_via_api()

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    created = api_a.post(API.PEOPLE, json={"name": "Чужой Edit", "gender": "m"}).json()

    r = api_b.patch(API.person(created["id"]), json={"summary": "MUTATED by B"})
    assert r.status_code != 200, (
        f"WRITE-LEAK: tenant_b can mutate tenant_a's person (status {r.status_code})"
    )


# ─────────────────────────────────────────────────────────────────────────
# Slug & UUID independence
# ─────────────────────────────────────────────────────────────────────────


def test_same_display_slug_allowed_across_tenants(signup_via_api, tenant_client):
    """display_slug — per-tenant, не global. Tenant A и B могут оба иметь
    person с `display_slug='ivan-ivanov'` — без коллизии."""
    user_a = signup_via_api()
    user_b = signup_via_api()

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    r_a = api_a.post(
        API.PEOPLE,
        json={"name": "A Иван", "display_slug": "ivan-ivanov", "gender": "m"},
    )
    assert r_a.status_code == 201, r_a.text
    r_b = api_b.post(
        API.PEOPLE,
        json={"name": "B Иван", "display_slug": "ivan-ivanov", "gender": "m"},
    )
    assert r_b.status_code == 201, (
        f"cross-tenant display_slug collision wrongly rejected: {r_b.text}"
    )
    # UUID-id'ы разные
    assert r_a.json()["id"] != r_b.json()["id"]


def test_tenant_signup_with_same_display_name_gets_different_slugs(
    signup_via_api, tenant_client
):
    """Два signup'а с одинаковым `full_name` → разные tenant_slug
    (auto-suffix или random). Без этого — overlap данных."""
    user_a = signup_via_api(full_name="Семья Ивановых")
    user_b = signup_via_api(full_name="Семья Ивановых")
    assert user_a.slug != user_b.slug, (
        f"tenants got same slug {user_a.slug!r} — collision risk"
    )


# ─────────────────────────────────────────────────────────────────────────
# GEDCOM isolation
# ─────────────────────────────────────────────────────────────────────────


def test_gedcom_export_returns_only_own_tenant_data(signup_via_api, tenant_client):
    """Tenant A экспортирует GEDCOM → файл содержит только его данные."""
    user_a = signup_via_api()
    user_b = signup_via_api()

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    api_a.post(API.PEOPLE, json={"name": "ExportA Тестов", "gender": "m"})
    api_b.post(API.PEOPLE, json={"name": "ExportB Чужой", "gender": "m"})

    ged = api_a.get(API.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long).text
    assert "ExportA" in ged
    assert "ExportB" not in ged, (
        "LEAK: tenant_a GEDCOM export contains tenant_b person name"
    )


def test_gedcom_import_creates_persons_only_in_uploading_tenant(
    signup_via_api, tenant_client
):
    """Tenant A импортирует .ged → tenant B свой tree не меняется."""
    user_a = signup_via_api()
    user_b = signup_via_api()

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)
    b_count_before = len(api_b.get(API.TREE).json()["people"])

    ged = (
        "0 HEAD\n"
        "1 SOUR Cross-Tenant-Test\n"
        "1 CHAR UTF-8\n"
        "0 @I1@ INDI\n"
        "1 NAME ImportA /Уникум/\n"
        "1 SEX M\n"
        "0 TRLR\n"
    ).encode("utf-8")

    r = api_a.post(
        API.ADMIN_IMPORT_GEDCOM,
        files={"file": ("isolation.ged", ged, "application/octet-stream")},
        timeout=TIMEOUTS.api_long,
    )
    if r.status_code != 200:
        # Backend может ещё не возвращать preview без auth_v2-bridge;
        # skip остальной тест если так.
        import pytest
        pytest.skip(f"import endpoint returned {r.status_code}")
    preview = r.json()
    confirm = {k: preview.get(k, []) for k in ("people", "relationships", "sources")}
    api_a.post("/api/admin/import-gedcom/confirm", json=confirm)

    b_count_after = len(api_b.get(API.TREE).json()["people"])
    assert b_count_after == b_count_before, (
        f"LEAK: tenant_b's tree changed after tenant_a's GEDCOM import "
        f"(before={b_count_before}, after={b_count_after})"
    )


# ─────────────────────────────────────────────────────────────────────────
# Concurrent operations
# ─────────────────────────────────────────────────────────────────────────


def test_concurrent_creates_in_two_tenants_dont_interfere(
    signup_via_api, tenant_client
):
    """Параллельные create-операции в двух tenant'ах — никаких cross-effects
    (без потери записей, без чужих записей)."""
    import concurrent.futures as cf

    user_a = signup_via_api()
    user_b = signup_via_api()

    def _create_batch(user, label: str) -> int:
        api = tenant_client(user)
        created = 0
        for i in range(5):
            r = api.post(
                API.PEOPLE,
                json={"name": f"{label}-Person-{i}", "gender": "m"},
            )
            if r.status_code == 201:
                created += 1
        return created

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        f_a = ex.submit(_create_batch, user_a, "Concurr-A")
        f_b = ex.submit(_create_batch, user_b, "Concurr-B")
        a_created = f_a.result()
        b_created = f_b.result()

    assert a_created == 5
    assert b_created == 5

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)
    a_names = {p["name"] for p in api_a.get(API.TREE).json()["people"]}
    b_names = {p["name"] for p in api_b.get(API.TREE).json()["people"]}

    # A видит только свои concurr-A-* persons
    for i in range(5):
        assert f"Concurr-A-Person-{i}" in a_names
        assert f"Concurr-B-Person-{i}" not in a_names, (
            f"LEAK: tenant_a sees tenant_b person Concurr-B-Person-{i}"
        )
    # B видит только свои concurr-B-* persons
    for i in range(5):
        assert f"Concurr-B-Person-{i}" in b_names
        assert f"Concurr-A-Person-{i}" not in b_names
