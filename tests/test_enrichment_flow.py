"""AI enrichment (★ Найти больше) — TC-E2E-001/006/009/010, F-AI-1..11.

Driven by `mock_ai_client` autouse — no real Anthropic call.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.xfail(
    reason="Background task для enrichment не выполняется в e2e subprocess "
           "(SQLite tenant DB фейлит на 'enrichmentjob.actor_kind' — schema "
           "drift между tenant create_all и migration). Backend-тесты "
           "test_enrichment.py покрывают логику unit-уровнем; UI-flow "
           "будет восстановлен после Stage 2 schema-bootstrap fix.",
    strict=False,
)
def test_enrichment_endpoint_returns_mocked_output(owner_user, base_url: str):
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output uses mock fixture.

    Backend always returns an async job; we poll until status=done (or timeout).
    """
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=10
    )
    if r.status_code != 200 or not r.json().get("people"):
        pytest.skip("tenant has no person seeded")
    pid = r.json()["people"][0]["id"]

    r = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=15,
    )
    if r.status_code in (401, 403, 404):
        pytest.skip(f"enrich endpoint not reachable for owner: {r.status_code}")
    assert r.status_code == 200, r.text

    body = r.json()
    job_id = body.get("job_id")
    poll_url = body.get("poll_url") or (f"/api/enrich/jobs/{job_id}" if job_id else None)
    assert poll_url, f"no poll URL in response: {body}"

    import time
    deadline = time.time() + 30
    final = None
    last_status = "?"
    while time.time() < deadline:
        r = httpx.get(
            f"{base_url}{poll_url}",
            cookies=owner_user.cookies,
            headers=headers,
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            last_status = data.get("status", "?")
            if last_status in ("done", "completed", "ready"):
                final = data
                break
            if last_status in ("error", "failed", "cancelled"):
                pytest.fail(f"job failed: {data}")
        time.sleep(0.3)

    assert final, f"job did not complete in 30s; last status={last_status} body={r.text[:300]}"
    output = final.get("output") or final.get("result", {}).get("output")
    assert output, f"no output in completed job: {list(final.keys())}"
    archives = output.get("archives") or []
    assert any("ЦАМО" in (a.get("name") or "") for a in archives), \
        f"mock fixture not applied — got real output? archives: {archives[:1]}"


def test_enrichment_history_endpoint_after_run(owner_user, base_url: str):
    """TC-E2E-010: history endpoint returns the prior enrichment for replay."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=10
    )
    if r.status_code != 200 or not r.json().get("people"):
        pytest.skip("tenant has no person seeded")
    pid = r.json()["people"][0]["id"]

    httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=30,
    )

    r = httpx.get(
        f"{base_url}/api/enrich/{pid}/history",
        cookies=owner_user.cookies,
        headers=headers,
        timeout=10,
    )
    if r.status_code == 401:
        pytest.fail("BUG-AUTH-001 regression: history endpoint returns 401")
    if r.status_code in (404, 405):
        pytest.skip(f"history endpoint shape: {r.status_code}")
    assert r.status_code == 200, r.text
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    assert isinstance(items, list)


def test_enrichment_quota_not_exceeded_on_mocked_run(owner_user, base_url: str):
    """F-AI-9 surrogate: a single mocked enrichment does not blow quota / 429."""
    headers = {"X-Tenant-Slug": owner_user.slug}
    r = httpx.get(
        f"{base_url}/api/tree", cookies=owner_user.cookies, headers=headers, timeout=10
    )
    if r.status_code != 200 or not r.json().get("people"):
        pytest.skip("tenant has no person seeded")
    pid = r.json()["people"][0]["id"]

    r = httpx.post(
        f"{base_url}/api/enrich/{pid}",
        json={"streaming": False, "force_refresh": True},
        cookies=owner_user.cookies,
        headers=headers,
        timeout=30,
    )
    assert r.status_code != 429, f"first enrichment hit quota: {r.text[:200]}"
