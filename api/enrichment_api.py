"""Typed wrappers for enrichment (AI) API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tenacity import retry, retry_if_result, stop_after_delay, wait_fixed

from api import routes
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from models.enrichment import EnrichJobResponse, EnrichStartResponse

if TYPE_CHECKING:
    import httpx


def start_enrichment(api: httpx.Client, person_id: str, *, force: bool = True) -> EnrichStartResponse:
    """POST /api/enrich/{pid} → validated EnrichStartResponse."""
    r = api.post(
        routes.enrich(person_id),
        json={"streaming": False, "force_refresh": force},
        timeout=TIMEOUTS.api_long,
    )
    return expect_response(r, label="start enrichment").status_ok().schema(EnrichStartResponse)


def poll_enrichment_job(api: httpx.Client, job_id: str) -> EnrichJobResponse:
    """Poll GET /api/enrich/jobs/{job_id} until status=done."""

    @retry(
        stop=stop_after_delay(TIMEOUTS.enrichment_poll),
        wait=wait_fixed(TIMEOUTS.polling_interval),
        retry=retry_if_result(lambda job: job.status != "done"),
        reraise=True,
    )
    def _poll() -> EnrichJobResponse:
        r = api.get(routes.enrich_jobs(job_id))
        r.raise_for_status()
        job = EnrichJobResponse.model_validate(r.json())
        assert job.status in ("queued", "running", "done"), f"unexpected job status: {job.status}"
        return job

    return _poll()
