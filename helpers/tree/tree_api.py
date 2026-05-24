"""Tree API helpers — people, relationships, lookup utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from api import routes
from api.person_api import get_people
from framework.response import expect_response
from models.person import RelationshipResponse
from src.texts import TestData

if TYPE_CHECKING:
    import httpx


def people(api: httpx.Client) -> list[dict[str, Any]]:
    """Fetch all people from /api/tree."""
    return [p.model_dump() for p in get_people(api)]


def relationships(api: httpx.Client) -> list[dict[str, Any]]:
    """Fetch all relationships from /api/relationships."""
    r = api.get(routes.RELATIONSHIPS)
    items = expect_response(r, label="GET relationships").status_ok().list_schema(RelationshipResponse)
    return [item.model_dump() for item in items]


def demo_parents_of_self(api: httpx.Client) -> dict[str, str]:
    """Returns {'m': father_id, 'f': mother_id} for demo-self."""
    people_by_id = {p["id"]: p for p in people(api)}
    rels = relationships(api)
    parent_rels = [
        r for r in rels
        if r["type"] == "parent" and r["person2_id"] == TestData.DEMO_PERSON_ID
    ]
    assert len(parent_rels) == 2, (
        f"expected demo-self to have 2 seeded parents; got {len(parent_rels)}: {parent_rels}"
    )
    result: dict[str, str] = {}
    for r in parent_rels:
        parent = people_by_id.get(r["person1_id"])
        assert parent, f"parent {r['person1_id']} not in tree"
        gender = parent.get("gender")
        assert gender in ("m", "f"), f"demo-parent {parent['id']} has invalid gender: {gender!r}"
        result[gender] = parent["id"]
    assert set(result) == {"m", "f"}, f"demo-self lacks one parent gender: {result}"
    return result


def find_person_by_name(api: httpx.Client, *substrings: str) -> dict[str, Any]:
    """Find a person whose name contains ALL given substrings. Asserts uniqueness."""
    matches = [
        p for p in people(api)
        if all(s in p["name"] for s in substrings)
    ]
    assert len(matches) == 1, (
        f"expected exactly 1 person matching {substrings!r}; got {len(matches)}: "
        f"{[p['name'] for p in matches]}"
    )
    return matches[0]


def people_count(api: httpx.Client) -> int:
    """Return the number of people in the tree."""
    return len(get_people(api))


def seed_person(api: httpx.Client, *, pid: str, name: str, **extra: Any) -> str:
    """POST /api/people с предсказуемым id (упрощает selectors внутри тестов).

    Backend (POST /api/people в main.py) принимает client-supplied id или
    сам генерирует UUID — фронт делает обоими путями. Тестам удобнее
    знать id заранее, чтобы делать `modal.pick_existing(pid)` без поиска
    по name через /api/tree.
    """
    body = {"id": pid, "name": name, "branch": "paternal", "gender": "m"}
    body.update(extra)
    api.post(routes.PEOPLE, json=body).raise_for_status()
    return pid


def demo_pid(api: httpx.Client) -> str:
    """Fetch the first seeded demo-person id from /api/tree."""
    ppl = get_people(api)
    assert ppl, "fresh tenant must have demo people seeded"
    return ppl[0].id
