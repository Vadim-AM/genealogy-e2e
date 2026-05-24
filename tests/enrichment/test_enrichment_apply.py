"""Enrichment-apply journey — accept an AI result into the card, revert it.

Owner runs AI enrichment on the demo-self card (mock AI), accepts a
hypothesis → it shows as a chip in the card → reverts it → the chip is
gone.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.err_msg import ErrMsg
from tests._core.messages import Enrichment, TestData, t
from tests._core.response import expect_response
from tests._core.step import step
from tests._models.enrichment import EnrichJobResponse
from tests.helpers.api import enrichment_api
from tests.pages.base import wait_for_authed_shell
from tests.pages.confirm_dialog import ConfirmDialog
from tests.pages.enrichment_modal import EnrichmentModal
from tests.pages.profile_panel import ProfilePanel


@allure.title("AI-обогащение: принятие гипотезы и откат через UI")
def test_owner_accepts_ai_hypothesis_into_card_then_reverts(
    owner_page: Page, owner_user, grant_ai_consent,
):
    """Owner runs AI enrichment, accepts a hypothesis → it appears as a
    chip in the card; reverts it → the chip is gone."""
    with step("подготовка: consent и открытие профиля"):
        grant_ai_consent(owner_user)

        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        wait_for_authed_shell(owner_page)

    with step("действие: запуск enrichment и принятие гипотезы"):
        panel.trigger_enrichment()

        # First enrich click → GDPR consent confirmDialog → run it.
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()
        dialog.confirm()

        modal = EnrichmentModal(owner_page)
        modal.expect_open()
        modal.wait_results()
        modal.accept_first_hypothesis()
        modal.close()

    with step("проверка: принятые факты отображаются как chips"):
        accepted = panel.accepted_facts_block
        expect(accepted, ErrMsg.element_not_visible).to_be_visible()
        chips = accepted.locator('[data-testid="profile-ai-chip"]')
        # Accepting the hypothesis writes its claim + reasoning as 2 chips.
        expect(chips, ErrMsg.wrong_count).to_have_count(2)

    with step("действие: откат принятой гипотезы"):
        chips.first.locator('[data-testid="profile-ai-chip-revert"]').click()
        # revert opens a prompt for an optional reason — confirm it.
        owner_page.get_by_role(
            "button", name=t(Enrichment.REVERT_OK), exact=True
        ).click()

    with step("проверка: chips исчезли после отката"):
        expect(chips, ErrMsg.wrong_count).to_have_count(0)


@allure.title("AI-обогащение: кэш отдаёт результат, health, фидбек и письма принимаются")
def test_enrichment_cache_and_health_invariants(
    owner_user, grant_ai_consent, tenant_client,
):
    """After an enrichment job finishes, its result is retrievable from
    the cache by id, and the api-key health endpoint reports its
    configuration. Neither has a dedicated UI — backend-invariant checks.
    """
    with step("подготовка: consent и запуск enrichment job"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)

        started = enrichment_api.start_enrichment(api, TestData.DEMO_PERSON_ID)

    with step("действие: polling до завершения job"):
        final = enrichment_api.poll_enrichment_job(api, started.job_id)
        enrichment_id = final.enrichment_id
        assert enrichment_id is not None, "enrichment job did not finish in time"

    with step("проверка: кэш, health, feedback и letters-sent"):
        cached = api.get(API.enrich_cache(enrichment_id))
        cached_job = expect_response(cached, label="GET enrich cache").status_ok().schema(EnrichJobResponse)
        assert cached_job.enrichment_id == enrichment_id, \
            f"cache enrichment_id: expected {enrichment_id}, got {cached_job.enrichment_id}"

        health = api.get(API.ENRICH_HEALTH_API_KEY)
        expect_response(health, label="GET enrich health").status_ok().json_has("configured")

        # Feedback + letter-sent telemetry — both keyed on the enrichment id.
        feedback = api.post(API.enrich_feedback(TestData.DEMO_PERSON_ID), json={
            "enrichment_id": enrichment_id, "feedback_type": "overall", "thumb": "up",
        })
        expect_response(feedback, label="POST enrich feedback").status_ok()

        letter = api.post(API.ENRICH_LETTERS_SENT, json={
            "enrichment_id": enrichment_id, "archive_name": "ЦАМО",
        })
        expect_response(letter, label="POST letters-sent").status_ok()
