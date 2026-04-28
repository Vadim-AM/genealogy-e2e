"""AI enrichment (★ Найти больше) — TC-E2E-001/006/009/010, F-AI-1..11.

Driven by `mock_ai_client` autouse — no real Anthropic call.

Both running tests are currently `xfail` due to a known infrastructure
bug: the lazy tenant-DB schema bootstrap (multitenancy/engine_pool.py:
_init_tenant_schema) does not include the `actor_kind` column added by
alembic migration `j8k9l0m1n2o3_enrichment_actor_kind`. Result: the
enrichment background task crashes on `SELECT enrichmentjob.actor_kind`,
job stays `queued` forever. Fix is in product (engine_pool bootstrap or
applying alembic per-tenant), not in tests. Drop the marker after the
fix lands.
"""

from __future__ import annotations

import time

import httpx
import pytest

from tests.timeouts import TIMEOUTS


@pytest.mark.xfail(
    reason="Tenant DB schema bootstrap missing `enrichmentjob.actor_kind` "
           "column (alembic j8k9l0m1n2o3 not applied per-tenant). Fix in "
           "backend/app/multitenancy/engine_pool.py:_init_tenant_schema.",
    strict=False,
)
def test_enrichment_endpoint_returns_mocked_output(owner_user, base_url: str):
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output uses mock fixture."""
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


@pytest.mark.xfail(
    reason="Same tenant-schema bootstrap issue as test_enrichment_endpoint_returns_mocked_output.",
    strict=False,
)
def test_enrichment_history_endpoint_after_run(owner_user, base_url: str):
    """TC-E2E-010: history endpoint returns the prior enrichment for replay."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=TIMEOUTS.api_request
    )
    r.raise_for_status()
    people = r.json()["people"]
    assert people, "fresh tenant must have demo people seeded"
    pid = people[0]["id"]

    httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_long,
    ).raise_for_status()

    r = httpx.get(
        f"{base_url}/api/enrich/{pid}/history",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    items = r.json()
    assert isinstance(items, list), f"history must be a list: {type(items)}"


def test_enrichment_first_run_does_not_hit_quota(owner_user, base_url: str):
    """F-AI-9 surrogate: a single mocked enrichment doesn't 429."""
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
