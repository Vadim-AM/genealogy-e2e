"""AI enrichment (★ Найти больше) — TC-E2E-001/006/009/010, F-AI-1..11.

Driven by `mock_ai_client` autouse — no real Anthropic call.

`test_enrichment_endpoint_returns_mocked_output` was xfailed under the
tenant-DB `actor_kind` bootstrap bug (BUG-DB-002 episode 4). Closed
by upstream commit `8146ed5` ("fix(enrichment): tenant-scoped session
factory for background jobs") on 28.04. Now a regular regression.

`test_enrichment_history_endpoint_returns_items_dict` is independent —
history endpoint reads `EnrichmentCache`, not `EnrichmentJob`, so the
`actor_kind` issue never blocked it.
"""

from __future__ import annotations

import time

import allure
import httpx

from tests.api_paths import API
from tests.helpers.tree.tree_api import demo_pid
from tests.response import expect_response
from tests.timeouts import TIMEOUTS


@allure.title("AI-обогащение: mock-результат содержит архивные подсказки")
def test_enrichment_endpoint_returns_mocked_output(
    owner_user, grant_ai_consent, tenant_client,
):
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output uses mock fixture."""
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)
    pid = demo_pid(api)

    r = api.post(
        API.enrich(pid),
        json={"streaming": False, "force_refresh": True},
        timeout=TIMEOUTS.api_long,
    )
    expect_response(r, label="POST enrich").status_ok()
    job_id = r.json()["job_id"]

    deadline = time.time() + TIMEOUTS.enrichment_poll
    final = None
    while time.time() < deadline:
        r = api.get(API.enrich_jobs(job_id), timeout=TIMEOUTS.api_short)
        r.raise_for_status()
        data = r.json()
        if data["status"] == "done":
            final = data
            break
        assert data["status"] in ("queued", "running"), f"unexpected job status: {data}"
        time.sleep(TIMEOUTS.polling_interval)

    assert final is not None, f"enrichment job did not complete in 30s; last: {data}"
    # Field renamed `archives` → `archive_suggestions` upstream (output_schema.json
    # tightened: `archive_suggestions` is now a required top-level property with
    # a fixed item shape). Pin the canonical name (Rule 7).
    archive_suggestions = final["output"]["archive_suggestions"]
    assert any("ЦАМО" in a["name"] for a in archive_suggestions), \
        f"mock fixture not applied — got real output? archive_suggestions: {archive_suggestions[:1]}"


@allure.title("AI-обогащение: история возвращает dict с ключом items")
def test_enrichment_history_endpoint_returns_items_dict(
    owner_user, grant_ai_consent, tenant_client,
):
    """TC-E2E-010 surrogate: GET /api/enrich/{pid}/history returns `{items: [...]}`.

    Контракт shape — backend всегда возвращает dict с ключом `items`
    (см. `backend/app/enrichment/router.py::get_history`), даже когда
    история пуста. Тест проверяет SHAPE, а не наполнение — содержимое
    зависит от завершения enrichment job.

    История читает `EnrichmentCache`, а не `EnrichmentJob`, поэтому
    `actor_kind`-баг этот endpoint не задевает.
    """
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)
    pid = demo_pid(api)

    r = api.get(API.enrich_history(pid))
    expect_response(r, label="GET enrich history").status_ok()
    data = r.json()
    assert isinstance(data, dict), (
        f"history must be a dict (got {type(data).__name__}): {data!r}"
    )
    assert isinstance(data.get("items"), list), (
        f"history.items must be a list "
        f"(got {type(data.get('items')).__name__}): {data!r}"
    )


@allure.title("AI-обогащение: первый запуск не упирается в квоту (429)")
def test_enrichment_first_run_does_not_hit_quota(
    owner_user, grant_ai_consent, tenant_client,
):
    """F-AI-9 surrogate: a single mocked enrichment doesn't 429."""
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)
    pid = demo_pid(api)

    r = api.post(
        API.enrich(pid),
        json={"streaming": False, "force_refresh": True},
        timeout=TIMEOUTS.api_long,
    )
    assert r.status_code != 429, (
        f"first enrichment hit quota: {r.request.method} {r.request.url} "
        f"status={r.status_code} body={r.text[:200]!r}"
    )
