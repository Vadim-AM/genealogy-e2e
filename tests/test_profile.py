"""Person profile rendering — F-PR-3, X-PR-1..5, TC-E2E-003 (canonical name).

These run against a fresh tenant where demo-self is the seeded subject.

Note (28.04 review): tests for profile-rendering / back-to-tree were removed
during sanitize wave — the originals only asserted URL preservation, which
is already covered by `test_tree_navigation::test_f5_keeps_profile_open`.
A real `test_profile_panel_shows_name` is owed once `pages/profile_panel.py`
is rewritten with concrete selectors (Wave 2).
"""

from __future__ import annotations

import httpx
import pytest


def test_canonical_name_assembled_from_split_fields(
    owner_user, base_url: str
):
    """TC-E2E-003: PATCH /api/people with surname/given_name/patronymic
    auto-composes canonical `name`."""
    headers = {"X-Tenant-Slug": owner_user.slug}

    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=10
    )
    assert r.status_code == 200, r.text
    tree = r.json()
    assert tree.get("people"), \
        f"tenant has no demo people seeded — signup_via_api should produce a demo tree; got {tree}"
    target = tree["people"][0]
    pid = target["id"]

    payload = {"surname": "Иванов", "given_name": "Иван", "patronymic": "Петрович"}
    r = httpx.patch(
        f"{base_url}/api/people/{pid}",
        json=payload,
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, \
        f"PATCH /api/people/{pid} failed (status={r.status_code}): {r.text[:300]}"

    r = httpx.get(
        f"{base_url}/api/people/{pid}",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    person = r.json()
    name = person.get("name") or ""
    for fragment in ("Иванов", "Иван", "Петрович"):
        assert fragment in name, f"canonical name missing '{fragment}': {name!r}"
