"""INV-AI-005: AI consent gate — backend enforcement.

`tests/test_enrichment_consent.py` (Wave 7) проверяет UI-side gate
через `confirm()` диалог. Backend gate ловит **API-driven** обход:
attacker дёргает POST `/api/enrich/{pid}` напрямую без consent.

Был xfail до commit `19fdd41` ("fix(enrichment): enforce
ai_consent_at gate on POST + history"). Regression-trail для 152-ФЗ /
GDPR compliance.
"""

from __future__ import annotations

from tests.api_paths import API
from tests.response import expect_response


def test_post_enrich_without_consent_is_forbidden(
    signup_via_api, tenant_client,
):
    """INV-AI-005: backend должен отбивать enrich-вызов до того, как
    пользователь записал явное согласие на AI processing.

    Was xfail until upstream commit `19fdd41`. Regression-trail.
    """
    user = signup_via_api()
    api = tenant_client(user)

    # Берём any person, пробуем enrich — НЕ дёргая ACCOUNT_AI_CONSENT.
    # Свежий user → ai_consent_at = NULL. Backend должен отбивать.
    r = api.get(API.TREE)
    expect_response(r, label="GET tree").status_ok()
    pid = (r.json().get("people") or [])[0]["id"]

    r = api.post(API.enrich(pid), json={"streaming": False, "force_refresh": True})

    expect_response(r, label="INV-AI-005: enrich without consent").status(403)
