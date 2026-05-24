"""TC-E2E-003: каноническое имя из split-полей."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

from api import person_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.person import PersonResponse
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("Каноническое имя собирается из фамилии, имени и отчества")
def test_canonical_name_assembled_from_split_fields(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """PATCH surname/given_name/patronymic собирает canonical name."""
    with step("подготовка: получить ID первой персоны из дерева"):
        api = tenant_client(owner_user)

        tree = person_api.get_tree(api)
        should.not_empty(tree.people, ErrMsg.tenant_no_demo_people)
        pid = tree.people[0].id

    with step("действие: PATCH surname/given_name/patronymic"):
        person_api.patch_person(api, pid, surname="Иванов", given_name="Иван", patronymic="Петрович")

    with step("проверка: каноническое имя содержит все фрагменты"):
        r = api.get(routes.person(pid))
        person = expect_response(r, label="GET person").status_ok().schema(PersonResponse)
        for fragment in ("Иванов", "Иван", "Петрович"):
            should.contain(person.name or "", fragment, ErrMsg.canonical_name_wrong)
