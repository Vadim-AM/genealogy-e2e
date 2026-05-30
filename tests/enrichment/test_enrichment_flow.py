"""AI enrichment (★ Найти больше) — TC-E2E-001/006/009/010, F-AI-1..11."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from api import enrichment_api, routes
from assertions.base import should
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from helpers.tree.tree_api import demo_pid
from models.enrichment import EnrichHistoryResponse
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("AI-обогащение: mock-результат содержит архивные подсказки")
def test_enrichment_endpoint_returns_mocked_output(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """F-AI-3: POST /api/enrich/{id} → job_id → poll → output содержит mock fixture."""
    with step("подготовка: consent и запуск enrichment"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        pid = demo_pid(api)

        started = enrichment_api.start_enrichment(api, pid)

    with step("действие: polling до завершения job"):
        final = enrichment_api.poll_enrichment_job(api, started.job_id)

    with step("проверка: mock-результат содержит ЦАМО"):
        output = should.not_none(final.output, ErrMsg.enrichment_output_none)
        archive_suggestions = output["archive_suggestions"]
        should.any_match(
            archive_suggestions,
            lambda a: "ЦАМО" in a["name"],
            ErrMsg.enrichment_mock_not_applied,
        )


@allure.title("AI-обогащение: история возвращает dict с ключом items")
def test_enrichment_history_endpoint_returns_items_dict(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """TC-E2E-010: GET /api/enrich/{pid}/history возвращает dict с ключом items."""
    with step("подготовка: consent и запрос истории"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)
        pid = demo_pid(api)

        r = api.get(routes.enrich_history(pid))
        expect_response(r, label="GET enrich history").status_ok()

    with step("проверка: ответ — dict с ключом items (list)"):
        history = EnrichHistoryResponse.model_validate(r.json())  # noqa: drift
        should.be_instance(history.items, list, ErrMsg.enrichment_history_not_list)


@allure.title("AI-обогащение: первый запуск не упирается в квоту (429)")
def test_enrichment_first_run_does_not_hit_quota(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """F-AI-9: одиночный mocked enrichment не возвращает 429."""
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
        should.not_equal(r.status_code, HTTPStatus.TOO_MANY_REQUESTS, ErrMsg.enrichment_not_429)
