"""AI enrichment (★ Найти больше) — TC-E2E-001/006/009/010, F-AI-1..11.

Driven by `mock_ai_client` autouse — no real Anthropic call.

`test_enrichment_endpoint_returns_mocked_output` was xfailed under the
tenant-DB `actor_kind` bootstrap bug (BUG-DB-002 episode 4). Closed
by upstream commit `8146ed5` ("fix(enrichment): tenant-scoped session
factory for background jobs") on 28.04. Now a regular regression.

`test_enrichment_history_endpoint_returns_items_dict` is independent —
history endpoint reads `EnrichmentCache`, not `EnrichmentJob`, so the
`actor_kind` issue never blocked it. Was previously xfailed by
mistake (different bug, unrelated assertion).
"""

from __future__ import annotations

import time

import httpx

from tests.timeouts import TIMEOUTS


def test_enrichment_endpoint_returns_mocked_output(
    owner_user, grant_ai_consent, base_url: str
):
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output uses mock fixture."""
    grant_ai_consent(owner_user)
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, "fresh tenant must have demo people seeded"
    pid = people[0]["id"]

    r = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    r.raise_for_status()
    body = r.json()
    job_id = body["job_id"]

    deadline = time.time() + TIMEOUTS.enrichment_poll
    final = None
    while time.time() < deadline:
        r = httpx.get(
            f"{base_url}/api/enrich/jobs/{job_id}",
            cookies=owner_user.cookies,
            headers=headers,
            timeout=TIMEOUTS.api_short,
        )
        r.raise_for_status()
        data = r.json()
        if data["status"] == "done":
            final = data
            break
        assert data["status"] in ("queued", "running"), f"unexpected job status: {data}"
        time.sleep(0.3)

    assert final is not None, f"enrichment job did not complete in 30s; last: {data}"
    output = final["output"]
    archives = output["archives"]
    assert any("ЦАМО" in a["name"] for a in archives), \
        f"mock fixture not applied — got real output? archives: {archives[:1]}"


def test_enrichment_history_endpoint_returns_items_dict(
    owner_user, grant_ai_consent, base_url: str
):
    """TC-E2E-010 surrogate: GET /api/enrich/{pid}/history returns `{items: [...]}`.

    Контракт shape — backend всегда возвращает dict с ключом `items`
    (см. `backend/app/enrichment/router.py::get_history`), даже когда
    история пуста. Тест проверяет SHAPE, а не наполнение — содержимое
    зависит от завершения enrichment job, что блокировано отдельным
    xfail (`test_enrichment_endpoint_returns_mocked_output`).

    История читает `EnrichmentCache`, а не `EnrichmentJob`, поэтому
    `actor_kind`-баг этот endpoint не задевает.
    """
    grant_ai_consent(owner_user)
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, "fresh tenant must have demo people seeded"
    pid = people[0]["id"]

    r = httpx.get(
        f"{base_url}/api/enrich/{pid}/history",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()
    assert isinstance(data, dict), (
        f"history must be a dict (got {type(data).__name__}): {data!r}"
    )
    assert isinstance(data.get("items"), list), (
        f"history.items must be a list "
        f"(got {type(data.get('items')).__name__}): {data!r}"
    )


def test_enrichment_first_run_does_not_hit_quota(
    owner_user, grant_ai_consent, base_url: str
):
    """F-AI-9 surrogate: a single mocked enrichment doesn't 429."""
    grant_ai_consent(owner_user)
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, "fresh tenant must have demo people seeded"
    pid = people[0]["id"]

    r = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    )
    assert r.status_code != 429, f"first enrichment hit quota: {r.text[:200]}"
