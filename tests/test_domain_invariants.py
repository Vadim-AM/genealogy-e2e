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

import pytest

from tests.constants import unique_email
from tests.messages import TestData


def _parent_rel(parent_id: str, child_id: str) -> dict:
    """Schema: `type=parent`, person1=parent, person2=child (directional)."""
    return {"type": "parent", "person1_id": parent_id, "person2_id": child_id}


def _person_payload(id: str, name: str, **extra) -> dict:
    base = {"id": id, "name": name, "branch": "paternal", "gender": "m"}
    base.update(extra)
    return base


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-001 / INV-DOMAIN-004 / INV-DATE-001 — date validation
# ─────────────────────────────────────────────────────────────────────────


def test_patch_person_death_before_birth_is_422(owner_user, tenant_client):
    """INV-DOMAIN-001: backend rejects death year < birth year.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        f"/api/people/{TestData.DEMO_PERSON_ID}",
        json={"birth": "1920", "death": "1900"},
    )
    assert r.status_code in (400, 422), (
        f"death(1900) before birth(1920) accepted: {r.status_code} {r.text[:200]}"
    )


def test_patch_parent_birth_after_child_is_422(signup_via_api, tenant_client):
    """INV-DOMAIN-004: parent.birth must precede child.birth (>= ~14y).

    Was xfail (partial fix until PATCH-handler validation). Closed by
    upstream batch-6/7. Now regular regression.
    """
    user = signup_via_api(email=unique_email("dom004"))
    api = tenant_client(user)

    api.post("/api/people", json=_person_payload(
        "dom004-child", "Ребёнок", branch="subject", birth="1985"
    )).raise_for_status()
    api.post("/api/people", json=_person_payload(
        "dom004-parent", "Родитель", birth="1960"
    )).raise_for_status()
    api.post("/api/relationships", json=_parent_rel("dom004-parent", "dom004-child")).raise_for_status()

    r = api.patch("/api/people/dom004-parent", json={"birth": "2000"})
    assert r.status_code in (400, 422), (
        f"parent.birth(2000) > child.birth(1985) accepted: "
        f"{r.status_code} {r.text[:200]}"
    )


def test_patch_person_garbage_birth_is_422(owner_user, tenant_client):
    """INV-DATE-001: birth='foobar' (non-parseable) must be rejected.

    Was xfail until upstream batch-6/7 (date format validator).
    Now regular regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        f"/api/people/{TestData.DEMO_PERSON_ID}",
        json={"birth": "foobar"},
    )
    assert r.status_code in (400, 422), (
        f"garbage birth='foobar' accepted: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-002 — >2 parents
# ─────────────────────────────────────────────────────────────────────────


def test_third_parent_relationship_is_rejected(signup_via_api, tenant_client):
    """INV-DOMAIN-002: backend should reject >2 parents per child.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
    user = signup_via_api(email=unique_email("dom002"))
    api = tenant_client(user)

    api.post("/api/people", json=_person_payload("dom002-child", "Ребёнок", branch="subject")).raise_for_status()
    for pid, pname in (("dom002-p1", "Родитель-1"), ("dom002-p2", "Родитель-2"), ("dom002-p3", "Родитель-3")):
        api.post("/api/people", json=_person_payload(pid, pname)).raise_for_status()

    api.post("/api/relationships", json=_parent_rel("dom002-p1", "dom002-child")).raise_for_status()
    api.post("/api/relationships", json=_parent_rel("dom002-p2", "dom002-child")).raise_for_status()

    r = api.post("/api/relationships", json=_parent_rel("dom002-p3", "dom002-child"))
    assert r.status_code in (400, 409, 422), (
        f"3rd parent accepted: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-003 — cycle in parent graph
# ─────────────────────────────────────────────────────────────────────────


def test_parent_cycle_is_rejected(signup_via_api, tenant_client):
    """INV-DOMAIN-003: A parent of B + B parent of A → backend rejects 2nd.

    Was xfail until upstream commit `7499d92`. Now regression.
    """
    user = signup_via_api(email=unique_email("dom003"))
    api = tenant_client(user)

    api.post("/api/people", json=_person_payload("dom003-a", "Цикл-A")).raise_for_status()
    api.post("/api/people", json=_person_payload("dom003-b", "Цикл-B")).raise_for_status()

    api.post("/api/relationships", json=_parent_rel("dom003-a", "dom003-b")).raise_for_status()

    r2 = api.post("/api/relationships", json=_parent_rel("dom003-b", "dom003-a"))
    assert r2.status_code in (400, 409, 422), (
        f"parent-cycle B→A→B accepted: {r2.status_code} {r2.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DOMAIN-005 — subject не может уйти на branch=demo
# ─────────────────────────────────────────────────────────────────────────


def test_subject_cannot_be_demoted_to_demo_branch(owner_user, tenant_client):
    """INV-DOMAIN-005: root subject can't have branch=demo.

    Was xfail until upstream batch-6/7. Now regular regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(f"/api/people/{TestData.DEMO_PERSON_ID}", json={"branch": "demo"})
    assert r.status_code in (400, 409, 422), (
        f"subject root demoted to branch=demo: {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-CASCADE-001 — DELETE non-root → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


def test_delete_non_root_person_with_relationship_does_not_500(
    signup_via_api, tenant_client,
):
    """INV-CASCADE-001: DELETE non-root person *с relationships* must
    not crash with 500. Изолированный person удалялся и без cascade-
    handling — реальный баг проявлялся когда есть FK.

    Was xfail at Run security 28.04 night. Closed by upstream batch-2.
    """
    user = signup_via_api(email=unique_email("cascade"))
    api = tenant_client(user)

    api.post("/api/people", json=_person_payload("cascade-child", "Ребёнок", branch="subject")).raise_for_status()
    api.post("/api/people", json=_person_payload("cascade-parent", "Родитель")).raise_for_status()
    api.post("/api/relationships", json=_parent_rel("cascade-parent", "cascade-child")).raise_for_status()

    r = api.delete("/api/people/cascade-parent")
    assert r.status_code != 500, (
        f"DELETE /api/people/cascade-parent crashed 500 — cascade not "
        f"handled. Body: {r.text[:300]}"
    )
    assert r.status_code < 500, f"unexpected 5xx: {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────
# INV-TXN-001 — orphan FK → 500 unhandled
# ─────────────────────────────────────────────────────────────────────────


def test_relationship_with_orphan_person_id_returns_404_not_500(
    signup_via_api, tenant_client,
):
    """INV-TXN-001: POST relationship referencing non-existent person
    must return 404 (or 422), never 500.

    Was xfail until upstream commit `4007a3a`. Now regression.
    """
    user = signup_via_api(email=unique_email("txn001"))
    api = tenant_client(user)

    api.post("/api/people", json=_person_payload("txn001-real", "Реальный")).raise_for_status()

    r = api.post(
        "/api/relationships",
        json={"type": "parent", "person1_id": "txn001-real", "person2_id": "NONEXIST-ORPHAN-ID"},
    )
    assert r.status_code != 500, (
        f"POST /api/relationships with orphan FK crashed 500. "
        f"Body: {r.text[:300]}"
    )
    assert r.status_code in (400, 404, 422), (
        f"orphan FK should return 4xx, got {r.status_code} {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# INV-DATA-001 — нет upper bound на размер surname/notes
# ─────────────────────────────────────────────────────────────────────────


def test_patch_person_huge_notes_is_rejected(owner_user, tenant_client):
    """INV-DATA-001: notes > reasonable bound (e.g. 10K) must be rejected.

    Was xfail until upstream commit `187bedb`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        f"/api/people/{TestData.DEMO_PERSON_ID}",
        json={"notes": "X" * (50 * 1024)},  # 50 KB
    )
    assert r.status_code in (400, 413, 422), (
        f"PATCH with 50KB notes accepted (status={r.status_code}) — "
        f"no upper-bound on text fields, DB inflation vector."
    )


def test_patch_person_huge_surname_is_rejected(owner_user, tenant_client):
    """INV-DATA-001: surname > reasonable bound (e.g. 100) must be rejected.

    Was xfail until upstream commit `187bedb`. Now regression.
    """
    api = tenant_client(owner_user)
    r = api.patch(
        f"/api/people/{TestData.DEMO_PERSON_ID}",
        json={"surname": "А" * 5_000},
    )
    assert r.status_code in (400, 413, 422), (
        f"PATCH with 5K-char surname accepted (status={r.status_code})."
    )
