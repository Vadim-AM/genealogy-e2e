"""Payload builders for tree domain invariant tests."""


def parent_rel(parent_id: str, child_id: str) -> dict:
    """Schema: `type=parent`, person1=parent, person2=child (directional)."""
    return {"type": "parent", "person1_id": parent_id, "person2_id": child_id}


def person_payload(id: str, name: str, **extra: object) -> dict:
    base: dict[str, object] = {"id": id, "name": name, "branch": "paternal", "gender": "m"}
    base.update(extra)
    return base
