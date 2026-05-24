"""Typed wrappers for enrichment (AI) API endpoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

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
    """Poll GET /api/enrich/jobs/{job_id} until done or timeout."""
    deadline = time.time() + TIMEOUTS.enrichment_poll
    while time.time() < deadline:
        r = api.get(routes.enrich_jobs(job_id))
        r.raise_for_status()
        job = EnrichJobResponse.model_validate(r.json())
        if job.status == "done":
            return job
        assert job.status in ("queued", "running"), f"unexpected job status: {job.status}"
        time.sleep(TIMEOUTS.polling_interval)
    msg = f"enrichment job {job_id} did not complete within {TIMEOUTS.enrichment_poll}s"
    raise TimeoutError(msg)
