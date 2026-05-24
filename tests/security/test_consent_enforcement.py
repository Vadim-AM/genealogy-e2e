"""INV-AI-005: AI consent gate — backend enforcement regression."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import routes
from api.person_api import get_tree
from framework.response import expect_response
from framework.step import step

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("AI-согласие: обогащение без consent отклоняется (403)")
def test_post_enrich_without_consent_is_forbidden(
    signup_via_api: Callable[..., AuthUser], tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Backend отбивает enrich-вызов до записи согласия на AI processing."""
    with step("подготовка: создать пользователя без AI-согласия"):
        user = signup_via_api()
        api = tenant_client(user)

    with step("подготовка: получить ID первой персоны из дерева"):
        # Берём any person, пробуем enrich — НЕ дёргая ACCOUNT_AI_CONSENT.
        # Свежий user → ai_consent_at = NULL. Backend должен отбивать.
        tree = get_tree(api)
        pid = tree.people[0].id

    with step("действие: вызвать enrich без consent"):
        r = api.post(routes.enrich(pid), json={"streaming": False, "force_refresh": True})

    with step("проверка: backend отбивает 403"):
        expect_response(r, label="INV-AI-005: enrich without consent").status(HTTPStatus.FORBIDDEN)
