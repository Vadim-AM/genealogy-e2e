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

from http import HTTPStatus

import allure

from tests._core import api_paths as routes
from tests._core.response import expect_response
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests.helpers.api import enrichment_api
from tests.helpers.tree.tree_api import demo_pid


@allure.title("AI-обогащение: mock-результат содержит архивные подсказки")
def test_enrichment_endpoint_returns_mocked_output(
    owner_user, grant_ai_consent, tenant_client,
):
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output uses mock fixture."""
    with step("подготовка: consent и запуск enrichment"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        pid = demo_pid(api)

        started = enrichment_api.start_enrichment(api, pid)

    with step("действие: polling до завершения job"):
        final = enrichment_api.poll_enrichment_job(api, started.job_id)

    with step("проверка: mock-результат содержит ЦАМО"):
        assert final.output is not None, "enrichment job output must not be None"
        # Field renamed `archives` → `archive_suggestions` upstream (output_schema.json
        # tightened: `archive_suggestions` is now a required top-level property with
        # a fixed item shape). Pin the canonical name (Rule 7).
        archive_suggestions = final.output["archive_suggestions"]
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
    with step("подготовка: consent и запрос истории"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        pid = demo_pid(api)

        r = api.get(routes.enrich_history(pid))
        expect_response(r, label="GET enrich history").status_ok()

    with step("проверка: ответ — dict с ключом items (list)"):
        from tests._models.enrichment import EnrichHistoryResponse
        history = EnrichHistoryResponse.model_validate(r.json())
        assert isinstance(history.items, list), (
            f"history.items must be a list "
            f"(got {type(history.items).__name__})"
        )


@allure.title("AI-обогащение: первый запуск не упирается в квоту (429)")
def test_enrichment_first_run_does_not_hit_quota(
    owner_user, grant_ai_consent, tenant_client,
):
    """F-AI-9 surrogate: a single mocked enrichment doesn't 429."""
    with step("подготовка: consent и запуск первого enrichment"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        pid = demo_pid(api)

        r = api.post(
            routes.enrich(pid),
            json={"streaming": False, "force_refresh": True},
            timeout=TIMEOUTS.api_long,
        )

    with step("проверка: не получили 429 (квота)"):
        # Keep raw call -- this is a negative/boundary assertion on status code
        assert r.status_code != HTTPStatus.TOO_MANY_REQUESTS, (
            f"first enrichment hit quota: {r.request.method} {r.request.url} "
            f"status={r.status_code} body={r.text[:200]!r}"
        )
