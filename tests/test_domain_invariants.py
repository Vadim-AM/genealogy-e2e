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


def _parent_rel(parent_id: str, child_id: str) -> dict:
    """Schema: `type=parent`, person1=parent, person2=child (directional)."""
    return {"type": "parent", "person1_id": parent_id, "person2_id": child_id}


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-001 / INV-DOMAIN-004 / INV-DATE-001 — date validation
# ─────────────────────────────────────────────────────────────────────────


def test_patch_person_death_before_birth_is_422(owner_user, base_url: str):
    """INV-DOMAIN-001: backend rejects death year < birth year.

    Was xfail until upstream commit `7499d92` ("feat(domain): validate
    dates, cycles, parent count, parent age"). Now regular regression.
    """
    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID,
        {"birth": "1920", "death": "1900"},
    )
    assert r.status_code in (400, 422), (
        f"death({1900}) before birth({1920}) accepted: "
        f"{r.status_code} {r.text[:200]}"
    )


@pytest.mark.xfail(
    reason="INV-DOMAIN-004 (partial fix): commit 7499d92 закрыл "
           "create-validation, но PATCH /api/people/{parent_id} с "
           "birth=2000 (после ребёнка 1985) всё ещё проходит → 200. "
           "Парные validation работают только на initial create. Fix: "
           "запустить ту же cross-field validation в PATCH handler "
           "(или в Pydantic schema, если parent_age — schema-level "
           "constraint).",
    strict=False,
)
def test_patch_parent_birth_after_child_is_422(signup_via_api, base_url: str):
    """INV-DOMAIN-004: parent.birth must precede child.birth (>= ~14y).

    Self-contained: создаём пару child + parent через API.
    """
    user = signup_via_api(email="dom004@e2e.example.com")

    child_id = "dom004-child"
    parent_id = "dom004-parent"

    _post_person(
        base_url, user,
        {"id": child_id, "name": "Ребёнок", "branch": "subject", "gender": "m", "birth": "1985"},
    ).raise_for_status()
    _post_person(
        base_url, user,
        {"id": parent_id, "name": "Родитель", "branch": "paternal", "gender": "m", "birth": "1960"},
    ).raise_for_status()
    _post_relationship(base_url, user, _parent_rel(parent_id, child_id)).raise_for_status()

    # Попытаться поставить parent.birth = 2000 (через 15 лет ПОСЛЕ ребёнка).
    r = _patch_person(base_url, user, parent_id, {"birth": "2000"})
    assert r.status_code in (400, 422), (
        f"parent.birth(2000) > child.birth(1985) accepted: "
        f"{r.status_code} {r.text[:200]}"
    )


@pytest.mark.xfail(
    reason="INV-DATE-001: birth='foobar' (произвольная строка) всё ещё "
           "принимается (Run security 28.04 + повторно после 7499d92 "
           "— тот фикс закрыл year-based cross-field check, но не парс "
           "формата). Backend хранит как opaque text. Fix: Pydantic "
           "regex/validator на birth/death — ISO 'YYYY' / 'YYYY-MM-DD' "
           "или approximate-форма ('~1900', 'до 1920') с whitelist.",
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


def test_third_parent_relationship_is_rejected(signup_via_api, base_url: str):
    """INV-DOMAIN-002: backend should reject >2 parents per child.

    Was xfail until upstream commit `7499d92`. Now regular regression.

    Self-contained: создаём child + 3 кандидата parent'а самостоятельно.
    """
    user = signup_via_api(email="dom002@e2e.example.com")

    child_id = "dom002-child"
    p1, p2, p3 = "dom002-p1", "dom002-p2", "dom002-p3"

    _post_person(base_url, user, {"id": child_id, "name": "Ребёнок", "branch": "subject", "gender": "m"}).raise_for_status()
    for pid, pname in ((p1, "Родитель-1"), (p2, "Родитель-2"), (p3, "Родитель-3")):
        _post_person(base_url, user, {"id": pid, "name": pname, "branch": "paternal", "gender": "m"}).raise_for_status()

    # Первые 2 parent — OK.
    _post_relationship(base_url, user, _parent_rel(p1, child_id)).raise_for_status()
    _post_relationship(base_url, user, _parent_rel(p2, child_id)).raise_for_status()

    # Третий — должен быть отбит.
    r = _post_relationship(base_url, user, _parent_rel(p3, child_id))
    assert r.status_code in (400, 409, 422), (
        f"3rd parent accepted: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-003 — cycle in parent graph
# ─────────────────────────────────────────────────────────────────────────


def test_parent_cycle_is_rejected(signup_via_api, base_url: str):
    """INV-DOMAIN-003: A parent of B + B parent of A → backend rejects 2nd.

    Was xfail until upstream commit `7499d92`. Now regular regression.
    """
    user = signup_via_api(email="dom003@e2e.example.com")

    a_id, b_id = "dom003-a", "dom003-b"
    _post_person(base_url, user, {"id": a_id, "name": "Цикл-A", "branch": "paternal", "gender": "m"}).raise_for_status()
    _post_person(base_url, user, {"id": b_id, "name": "Цикл-B", "branch": "paternal", "gender": "m"}).raise_for_status()

    # 1. A parent of B — OK.
    _post_relationship(base_url, user, _parent_rel(a_id, b_id)).raise_for_status()

    # 2. B parent of A — должно быть отбито (создаёт cycle).
    r2 = _post_relationship(base_url, user, _parent_rel(b_id, a_id))
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


# ─────────────────────────────────────────────────────────────────────────
# INV-CASCADE-001 / INV-PERM-003b — DELETE non-root → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


def test_delete_non_root_person_with_relationship_does_not_500(
    signup_via_api, base_url: str,
):
    """INV-CASCADE-001: DELETE non-root person *с relationships* must
    not crash with 500. Изолированный person удаляется и без cascade-
    кода — реальный баг проявлялся когда есть FK на этот person.

    Was xfail на момент Run security 28.04 night (DELETE crashed 500
    из-за unhandled FK violation). Прошёл на dev tip 63edf35 — оставляю
    как regression-trail.
    """
    user = signup_via_api(email="cascade@e2e.example.com")

    # Создаём пару child + parent + relationship — DELETE parent должен
    # cascade-снять relationship. Это и есть путь к 500.
    child_id = "cascade-child"
    parent_id = "cascade-parent"
    _post_person(base_url, user, {"id": child_id, "name": "Ребёнок", "branch": "subject", "gender": "m"}).raise_for_status()
    _post_person(base_url, user, {"id": parent_id, "name": "Родитель", "branch": "paternal", "gender": "m"}).raise_for_status()
    _post_relationship(base_url, user, _parent_rel(parent_id, child_id)).raise_for_status()

    r = httpx.delete(
        f"{base_url}/api/people/{parent_id}",
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code != 500, (
        f"DELETE /api/people/{parent_id} crashed 500 — cascade not "
        f"handled. Body: {r.text[:300]}"
    )
    assert r.status_code < 500, f"unexpected 5xx: {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────
# INV-TXN-001 — orphan FK → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


def test_relationship_with_orphan_person_id_returns_404_not_500(
    signup_via_api, base_url: str,
):
    """INV-TXN-001: POST relationship referencing non-existent person
    must return 404 (or 422), never 500.

    Was xfail until upstream commit `4007a3a` ("fix(api): cascade
    enrichment+photo on delete + 404 на orphan rel ref"). Now regular.
    """
    user = signup_via_api(email="txn001@e2e.example.com")

    # Создаём ОДНОГО real person — второй person_id будет orphan.
    real_id = "txn001-real"
    _post_person(
        base_url, user,
        {"id": real_id, "name": "Реальный", "branch": "paternal", "gender": "m"},
    ).raise_for_status()

    r = _post_relationship(
        base_url, user,
        {"type": "parent", "person1_id": real_id, "person2_id": "NONEXIST-ORPHAN-ID"},
    )
    assert r.status_code != 500, (
        f"POST /api/relationships with orphan FK crashed with 500 — "
        f"unhandled FK violation. Body: {r.text[:300]}"
    )
    assert r.status_code in (400, 404, 422), (
        f"orphan FK should return 4xx with proper detail, got "
        f"{r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DATA-001 — нет upper bound на размер surname/notes
# ─────────────────────────────────────────────────────────────────────────


def test_patch_person_huge_notes_is_rejected(owner_user, base_url: str):
    """INV-DATA-001: notes > reasonable bound (e.g. 10K) must be rejected.

    Was xfail until upstream commit `187bedb` ("fix(schemas): max_length
    на text-полях Person"). Now regular regression.
    """
    huge_notes = "X" * (50 * 1024)  # 50 KB — clearly above any reasonable bound

    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID, {"notes": huge_notes}
    )
    assert r.status_code in (400, 413, 422), (
        f"PATCH with 50KB notes accepted (status={r.status_code}) — "
        f"no upper-bound on text fields, DB inflation vector."
    )


def test_patch_person_huge_surname_is_rejected(owner_user, base_url: str):
    """INV-DATA-001: surname > reasonable bound (e.g. 100) must be rejected.

    Was xfail until upstream commit `187bedb`. Now regular regression.
    """
    r = _patch_person(
        base_url, owner_user, TestData.DEMO_PERSON_ID,
        {"surname": "А" * 5_000},
    )
    assert r.status_code in (400, 413, 422), (
        f"PATCH with 5K-char surname accepted (status={r.status_code})."
    )
