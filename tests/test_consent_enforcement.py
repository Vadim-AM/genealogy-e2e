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
    r.raise_for_status()
    pid = (r.json().get("people") or [])[0]["id"]

    r = api.post(API.enrich(pid), json={"streaming": False, "force_refresh": True})

    assert r.status_code in (401, 403, 422), (
        f"INV-AI-005: enrich accepted without consent (status="
        f"{r.status_code}). Backend should require consent on record "
        f"before sending PII to Anthropic. Body: {r.text[:200]}"
    )
