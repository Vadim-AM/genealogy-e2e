"""INV-AI-005: AI consent gate — backend enforcement.

`tests/test_enrichment_consent.py` (Wave 7) проверяет UI-side gate:
кликнуть «★ Найти больше» без consent → frontend показывает
`confirm()` и блокирует POST до accept. Это **frontend-gate** —
attacker может обойти, дёрнув POST `/api/enrich/{pid}` напрямую.

Backend gate должен быть:
- POST `/api/enrich/{pid}` **без** `ai_consent_at` в profile → 403.
- После revoke consent → история через `/api/enrich/{pid}/history`
  тоже должна быть скрыта (или возвращать только non-AI данные).

Run security 28.04 night confirmed: backend пропускает enrich-call
без consent → 200 + job. Compliance 152-ФЗ ст. 9 ч. 1 / GDPR ст. 7
обходится — данные ушли в Anthropic без legal-grade согласия.

Здесь покрывается основной случай: prereq-call без consent должен
быть 403. Дополнительный edge (history после revoke) — TBD.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"


def test_post_enrich_without_consent_is_forbidden(
    signup_via_api, base_url: str
):
    """INV-AI-005: backend должен отбивать enrich-вызов до того, как
    пользователь записал явное согласие на AI processing.

    Was xfail until upstream commit `19fdd41` ("fix(enrichment):
    enforce ai_consent_at gate on POST + history"). Now regular
    regression — keeps the consent gate strict.
    """
    email = f"consent-{uuid.uuid4().hex[:8]}@e2e.example.com"
    user = signup_via_api(email=email)
    headers = {"X-Tenant-Slug": user.slug}

    # Берём any person, пробуем enrich — НЕ дёргая /api/account/me/ai-consent.
    # Свежий user → ai_consent_at = NULL. Если backend доверяет frontend
    # localStorage и пропускает — это и есть баг.
    r = httpx.get(
        f"{base_url}/api/tree", cookies=user.cookies, headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    people = r.json().get("people") or []
    assert people, "fresh tenant must have at least one demo person"
    pid = people[0]["id"]

    r = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )

    assert r.status_code in (401, 403, 422), (
        f"INV-AI-005: enrich accepted without consent (status="
        f"{r.status_code}). Backend should require consent on record "
        f"before sending PII to Anthropic. Body: {r.text[:200]}"
    )
