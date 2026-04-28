"""Domain invariants — INV-DOMAIN-001..005, INV-DATE-001.

Backend хранит persons + relationships. У этих сущностей есть
**доменные инварианты**, которые backend обязан валидировать
независимо от frontend (frontend может скрыть кнопку, но прямой
PATCH/POST через API должен отбиваться).

Найдено в QA Run domain/security 28.04 night:

| ID | Symptom | API path |
|---|---|---|
| INV-DOMAIN-001 | death < birth → 200 | PATCH /api/people/{id} |
| INV-DOMAIN-002 | >2 parents → 201 | POST /api/relationships |
| INV-DOMAIN-003 | A parent of B + B parent of A → 201/201 | POST /api/relationships |
| INV-DOMAIN-004 | mother born ПОСЛЕ child (>=1y) → 200 | PATCH /api/people/{id} |
| INV-DOMAIN-005 | branch=demo для subject → 200 | PATCH /api/people/{root_id} |
| INV-DATE-001   | birth='foobar' (не parsed дата) → 201/200 | POST или PATCH /api/people |

Все xfail до продукт-фикса.
"""

from __future__ import annotations

import httpx
import pytest

from tests.messages import TestData
from tests.timeouts import TIMEOUTS


def _patch_person(base_url: str, user, pid: str, payload: dict) -> httpx.Response:
    return httpx.patch(
        f"{base_url}/api/people/{pid}",
        json=payload,
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )


def _post_person(base_url: str, user, payload: dict) -> httpx.Response:
    return httpx.post(
        f"{base_url}/api/people",
        json=payload,
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )


def _post_relationship(base_url: str, user, payload: dict) -> httpx.Response:
    return httpx.post(
        f"{base_url}/api/relationships",
        json=payload,
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )


def _list_parents_via_tree(base_url: str, user, pid: str) -> list[str]:
    """Через /api/tree найти список parent IDs для person pid."""
    r = httpx.get(
        f"{base_url}/api/tree",
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    parents: list[str] = []
    for rel in r.json().get("relationships", []):
        if rel.get("type") == "parent" and rel.get("child_id") == pid:
            parents.append(rel.get("parent_id"))
    return parents


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-001 / INV-DOMAIN-004 / INV-DATE-001 — date validation
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="INV-DOMAIN-001: backend не валидирует death < birth. "
           "PATCH demo-self с birth=1920, death=1900 → 200 (Run "
           "domain 28.04). Fix: добавить cross-field check в "
           "Person Pydantic schema, либо проверка перед commit'ом "
           "в /api/people PATCH handler.",
    strict=False,
)
def test_patch_person_death_before_birth_is_422(owner_user, base_url: str):
    """INV-DOMAIN-001: backend rejects death year < birth year."""
    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID,
        {"birth": "1920", "death": "1900"},
    )
    assert r.status_code in (400, 422), (
        f"death({1900}) before birth({1920}) accepted: "
        f"{r.status_code} {r.text[:200]}"
    )


@pytest.mark.xfail(
    reason="INV-DOMAIN-004: mother (или any parent) born ПОСЛЕ child "
           "→ 200 (Run domain 28.04). Если у demo-self birth=1985 и "
           "PATCH demo-mother.birth=2000 — backend принимает. Fix: "
           "проверять birth-year родителей >= birth-year child + N "
           "(биологический минимум, ~12 лет; разумно 14-15).",
    strict=False,
)
def test_patch_parent_birth_after_child_is_422(signup_via_api, base_url: str):
    """INV-DOMAIN-004: parent.birth must precede child.birth (> ~14 years)."""
    user = signup_via_api(email="dom004@e2e.example.com")

    # PATCH демо-self → birth=1985 (ребёнок).
    _patch_person(base_url, user, TestData.DEMO_PERSON_ID, {"birth": "1985"}).raise_for_status()
    # Найти родителя.
    parents = _list_parents_via_tree(base_url, user, TestData.DEMO_PERSON_ID)
    assert parents, "demo-self has no parents seeded — fixture changed?"
    parent_id = parents[0]

    # Попытаться поставить parent.birth = 2000 (через 15 лет ПОСЛЕ ребёнка).
    r = _patch_person(base_url, user, parent_id, {"birth": "2000"})
    assert r.status_code in (400, 422), (
        f"parent.birth(2000) > child.birth(1985) accepted: "
        f"{r.status_code} {r.text[:200]}"
    )


@pytest.mark.xfail(
    reason="INV-DATE-001: birth='foobar' (любая мусорная строка) → "
           "201/200 (Run domain 28.04). Backend хранит как opaque "
           "text вместо parse + reject. Fix: Pydantic regex/validator "
           "на birth/death — либо ISO 'YYYY' / 'YYYY-MM-DD', либо "
           "approximate-форма ('~1900', 'до 1920') с whitelist.",
    strict=False,
)
def test_patch_person_garbage_birth_is_422(owner_user, base_url: str):
    """INV-DATE-001: birth='foobar' (non-parseable) must be rejected."""
    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID,
        {"birth": "foobar"},
    )
    assert r.status_code in (400, 422), (
        f"garbage birth='foobar' accepted: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-002 — >2 parents
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="INV-DOMAIN-002: backend позволяет 3-ий parent relationship "
           "(Run domain 28.04). Frontend скрывает кнопку «+» когда "
           "уже 2 parents — но это cosmetic, прямой POST "
           "/api/relationships принимается. Fix: server-side check на "
           "RELATIVE_LIMITS.parents=2 перед commit'ом в "
           "/api/relationships handler (или в Relationship schema).",
    strict=False,
)
def test_third_parent_relationship_is_rejected(signup_via_api, base_url: str):
    """INV-DOMAIN-002: backend should reject >2 parents per child."""
    user = signup_via_api(email="dom002@e2e.example.com")

    # Создаём 3-его кандидата в parent'ы (у demo-self уже 2 demo-parent'а).
    pcand = _post_person(
        base_url, user,
        {"name": "Третий Родитель", "branch": "paternal", "gender": "m"},
    )
    pcand.raise_for_status()
    cand_id = pcand.json()["id"]

    r = _post_relationship(
        base_url, user,
        {"type": "parent", "parent_id": cand_id, "child_id": TestData.DEMO_PERSON_ID},
    )
    assert r.status_code in (400, 409, 422), (
        f"3rd parent accepted: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-003 — cycle in parent graph
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="INV-DOMAIN-003: parent-cycle (A parent of B + B parent of A) "
           "принимается обоими POST /api/relationships → 201/201 (Run "
           "domain 28.04). DFS от любого узла → infinite recursion. "
           "Fix: при insert relationship 'parent' проверять, что новый "
           "edge не создаёт cycle (BFS от ancestor по parent edges).",
    strict=False,
)
def test_parent_cycle_is_rejected(signup_via_api, base_url: str):
    """INV-DOMAIN-003: A parent of B + B parent of A → backend rejects 2nd."""
    user = signup_via_api(email="dom003@e2e.example.com")

    a = _post_person(base_url, user, {"name": "Цикл-A", "branch": "paternal", "gender": "m"})
    a.raise_for_status()
    a_id = a.json()["id"]

    b = _post_person(base_url, user, {"name": "Цикл-B", "branch": "paternal", "gender": "m"})
    b.raise_for_status()
    b_id = b.json()["id"]

    # 1. A parent of B — OK.
    r1 = _post_relationship(base_url, user, {"type": "parent", "parent_id": a_id, "child_id": b_id})
    r1.raise_for_status()

    # 2. B parent of A — должно быть отбито (создаёт cycle).
    r2 = _post_relationship(base_url, user, {"type": "parent", "parent_id": b_id, "child_id": a_id})
    assert r2.status_code in (400, 409, 422), (
        f"parent-cycle B→A→B accepted: {r2.status_code} {r2.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-005 — subject не может уйти на branch=demo
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="INV-DOMAIN-005: PATCH demo-self с branch=demo → 200 (Run "
           "domain 28.04). Затем «Удалить демо» в Опасной зоне сметёт "
           "и subject-карточку — пространство останется без anchor, "
           "родственники без центра. Fix: запретить branch=demo для "
           "person.id == tenant.root_id (server-side check в PATCH "
           "/api/people/{id}).",
    strict=False,
)
def test_subject_cannot_be_demoted_to_demo_branch(owner_user, base_url: str):
    """INV-DOMAIN-005: root subject can't have branch=demo."""
    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID, {"branch": "demo"}
    )
    assert r.status_code in (400, 409, 422), (
        f"subject root demoted to branch=demo: {r.status_code} {r.text[:200]}"
    )
