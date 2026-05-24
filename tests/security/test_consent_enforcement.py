"""INV-AI-005: AI consent gate — backend enforcement.

`tests/test_enrichment_consent.py` (Wave 7) проверяет UI-side gate
через `confirm()` диалог. Backend gate ловит **API-driven** обход:
attacker дёргает POST `/api/enrich/{pid}` напрямую без consent.

Был xfail до commit `19fdd41` ("fix(enrichment): enforce
ai_consent_at gate on POST + history"). Regression-trail для 152-ФЗ /
GDPR compliance.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import routes
from framework.response import expect_response
from framework.step import step


@allure.title("AI-согласие: обогащение без consent отклоняется (403)")
def test_post_enrich_without_consent_is_forbidden(
    signup_via_api, tenant_client,
) -> None:
    """INV-AI-005: backend должен отбивать enrich-вызов до того, как
    пользователь записал явное согласие на AI processing.

    Was xfail until upstream commit `19fdd41`. Regression-trail.
    """
    with step("подготовка: создать пользователя без AI-согласия"):
        user = signup_via_api()
        api = tenant_client(user)

    with step("подготовка: получить ID первой персоны из дерева"):
        # Берём any person, пробуем enrich — НЕ дёргая ACCOUNT_AI_CONSENT.
        # Свежий user → ai_consent_at = NULL. Backend должен отбивать.
        r = api.get(routes.TREE)
        expect_response(r, label="GET tree").status_ok()
        pid = (r.json().get("people") or [])[0]["id"]

    with step("действие: вызвать enrich без consent"):
        r = api.post(routes.enrich(pid), json={"streaming": False, "force_refresh": True})

    with step("проверка: backend отбивает 403"):
        expect_response(r, label="INV-AI-005: enrich without consent").status(HTTPStatus.FORBIDDEN)
