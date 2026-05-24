"""Person profile rendering — F-PR-3, X-PR-1..5, TC-E2E-003 (canonical name).

These run against a fresh tenant where demo-self is the seeded subject.

Note (28.04 review): tests for profile-rendering / back-to-tree were removed
during sanitize wave — the originals only asserted URL preservation, which
is already covered by `test_tree_navigation::test_f5_keeps_profile_open`.
A real `test_profile_panel_shows_name` is owed once `pages/profile_panel.py`
is rewritten with concrete selectors (Wave 2).
"""

from __future__ import annotations

import allure

from api import person_api, routes
from framework.response import expect_response
from framework.step import step
from models.person import PersonResponse


@allure.title("Каноническое имя собирается из фамилии, имени и отчества")
def test_canonical_name_assembled_from_split_fields(owner_user, tenant_client) -> None:
    """TC-E2E-003: PATCH /api/people with surname/given_name/patronymic
    auto-composes canonical `name`."""
    with step("подготовка: получить ID первой персоны из дерева"):
        api = tenant_client(owner_user)

        tree = person_api.get_tree(api)
        assert tree.people, \
            "tenant has no demo people seeded — signup_via_api should produce a demo tree"
        pid = tree.people[0].id

    with step("действие: PATCH surname/given_name/patronymic"):
        person_api.patch_person(api, pid, surname="Иванов", given_name="Иван", patronymic="Петрович")

    with step("проверка: каноническое имя содержит все фрагменты"):
        r = api.get(routes.person(pid))
        person = expect_response(r, label="GET person").status_ok().schema(PersonResponse)
        for fragment in ("Иванов", "Иван", "Петрович"):
            assert fragment in (person.name or ""), f"canonical name missing '{fragment}': {person.name!r}"
