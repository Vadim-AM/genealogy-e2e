"""Enrichment-apply journey — принятие AI-гипотезы и откат через UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import enrichment_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from models.enrichment import EnrichJobResponse
from pages.confirm_dialog import ConfirmDialog
from pages.enrichment_modal import EnrichmentModal
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.users import AuthUser


@allure.title("AI-обогащение: принятие гипотезы и откат через UI")
def test_owner_accepts_ai_hypothesis_into_card_then_reverts(
    owner_page: Page, owner_user: AuthUser, grant_ai_consent: Callable[[AuthUser], None]
) -> None:
    """Owner принимает AI-гипотезу → chip в карточке → откат → chip исчез."""
    with step("подготовка: consent и открытие профиля"):
        grant_ai_consent(owner_user)

        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        TreePage(owner_page).expect_authed_state()

    with step("действие: запуск enrichment и принятие гипотезы"):
        panel.trigger_enrichment()

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
        expect(panel.accepted_chips, ErrMsg.wrong_count).to_have_count(2)

    with step("действие: откат принятой гипотезы"):
        panel.revert_first_chip()
        panel.confirm_revert()

    with step("проверка: chips исчезли после отката"):
        expect(panel.accepted_chips, ErrMsg.wrong_count).to_have_count(0)


@allure.title("AI-обогащение: кэш отдаёт результат, health, фидбек и письма принимаются")
def test_enrichment_cache_and_health_invariants(
    owner_user: AuthUser,
    grant_ai_consent: Callable[[AuthUser], None],
    tenant_client: Callable[[AuthUser], httpx.Client],
) -> None:
    """Кэш отдаёт результат по id, health отвечает, feedback и letters принимаются."""
    with step("подготовка: consent и запуск enrichment job"):
        grant_ai_consent(owner_user)
        api = tenant_client(owner_user)

        started = enrichment_api.start_enrichment(api, TestData.DEMO_PERSON_ID)

    with step("действие: polling до завершения job"):
        final = enrichment_api.poll_enrichment_job(api, started.job_id)
        enrichment_id = final.enrichment_id
        should.not_none(enrichment_id, ErrMsg.enrichment_id_missing)

    with step("проверка: кэш, health, feedback и letters-sent"):
        cached = api.get(routes.enrich_cache(enrichment_id))
        cached_job = expect_response(cached, label="GET enrich cache").status_ok().schema(EnrichJobResponse)
        should.be_equal(cached_job.enrichment_id, enrichment_id, ErrMsg.enrichment_cache_id_mismatch)

        health = api.get(routes.ENRICH_HEALTH_API_KEY)
        expect_response(health, label="GET enrich health").status_ok().json_has("configured")

        feedback = api.post(
            routes.enrich_feedback(TestData.DEMO_PERSON_ID),
            json={
                "enrichment_id": enrichment_id,
                "feedback_type": "overall",
                "thumb": "up",
            },
        )
        expect_response(feedback, label="POST enrich feedback").status_ok()

        letter = api.post(
            routes.ENRICH_LETTERS_SENT,
            json={
                "enrichment_id": enrichment_id,
                "archive_name": "ЦАМО",
            },
        )
        expect_response(letter, label="POST letters-sent").status_ok()
