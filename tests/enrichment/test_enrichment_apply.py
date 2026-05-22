"""Enrichment-apply journey — accept an AI result into the card, revert it.

Owner runs AI enrichment on the demo-self card (mock AI), accepts a
hypothesis → it shows as a chip in the card → reverts it → the chip is
gone.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import AiConsent, Enrichment, TestData, t
from tests.pages.enrichment_modal import EnrichmentModal
from tests.pages.profile_panel import ProfilePanel
from tests.timeouts import TIMEOUTS


def test_owner_accepts_ai_hypothesis_into_card_then_reverts(
    owner_page: Page, owner_user, grant_ai_consent,
):
    """Owner runs AI enrichment, accepts a hypothesis → it appears as a
    chip in the card; reverts it → the chip is gone."""
    grant_ai_consent(owner_user)

    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("domcontentloaded")

    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.trigger_enrichment()

    # First enrich click → GDPR consent confirmDialog → run it.
    owner_page.locator(".confirm-dialog").get_by_role(
        "button", name=t(AiConsent.CONFIRM_LABEL)
    ).click()

    modal = EnrichmentModal(owner_page)
    modal.expect_open()
    modal.wait_results()
    modal.accept_first_hypothesis()
    modal.close()

    accepted = panel.accepted_facts_block
    expect(accepted).to_be_visible()
    chips = accepted.locator(".profile-ai-chip")
    # Accepting the hypothesis writes its claim + reasoning as 2 chips.
    expect(chips).to_have_count(2)

    chips.first.locator(".profile-ai-chip-revert").click()
    # revert opens a prompt for an optional reason — confirm it.
    owner_page.get_by_role(
        "button", name=t(Enrichment.REVERT_OK), exact=True
    ).click()
    expect(chips).to_have_count(0)


def test_enrichment_cache_and_health_invariants(
    owner_user, grant_ai_consent, tenant_client,
):
    """After an enrichment job finishes, its result is retrievable from
    the cache by id, and the api-key health endpoint reports its
    configuration. Neither has a dedicated UI — backend-invariant checks.
    """
    grant_ai_consent(owner_user)
    api = tenant_client(owner_user)

    started = api.post(
        API.enrich(TestData.DEMO_PERSON_ID),
        json={"streaming": False, "force_refresh": True},
        timeout=TIMEOUTS.api_long,
    )
    started.raise_for_status()
    job_id = started.json()["job_id"]

    enrichment_id = None
    deadline = time.time() + TIMEOUTS.enrichment_poll
    while time.time() < deadline:
        job = api.get(API.enrich_jobs(job_id))
        job.raise_for_status()
        body = job.json()
        if body["status"] == "done":
            enrichment_id = body["enrichment_id"]
            break
        assert body["status"] in ("queued", "running"), body
        time.sleep(TIMEOUTS.polling_interval)
    assert enrichment_id is not None, "enrichment job did not finish in time"

    cached = api.get(API.enrich_cache(enrichment_id))
    cached.raise_for_status()
    assert cached.json()["enrichment_id"] == enrichment_id, \
        "cache endpoint must return the same enrichment by id"

    health = api.get(API.ENRICH_HEALTH_API_KEY)
    health.raise_for_status()
    assert "configured" in health.json(), \
        "api-key health must report a `configured` flag"

    # Feedback + letter-sent telemetry — both keyed on the enrichment id.
    feedback = api.post(API.enrich_feedback(TestData.DEMO_PERSON_ID), json={
        "enrichment_id": enrichment_id, "feedback_type": "overall", "thumb": "up",
    })
    feedback.raise_for_status()

    letter = api.post(API.ENRICH_LETTERS_SENT, json={
        "enrichment_id": enrichment_id, "archive_name": "ЦАМО",
    })
    letter.raise_for_status()
