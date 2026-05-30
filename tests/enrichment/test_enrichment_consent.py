"""TC-AI-1: GDPR/152-FZ consent dialog перед первым ★ Найти больше."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from pages.confirm_dialog import ConfirmDialog
from pages.profile_panel import ProfilePanel
from src.texts import AiConsent, ErrMsg, TestData, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("AI-согласие: первый клик показывает модалку с Anthropic и политикой")
def test_first_enrich_click_renders_consent_modal_with_legal_content(
    owner_page: Page,
    pages: PageFactory,
) -> None:
    """TC-AI-1 (positive): первый click ★ → modal с Anthropic + privacy policy."""
    with step("действие: открыть профиль и кликнуть обогащение"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        panel.trigger_enrichment()
        dialog = pages.create(ConfirmDialog)
        dialog.expect_visible()

    with step("проверка: модалка содержит Anthropic, политику и shared data"):
        msg = dialog.text()
        should.contain(msg, AiConsent.PROVIDER, ErrMsg.consent_provider_missing)
        should.contain(msg.lower(), t(AiConsent.POLICY_KEYWORD), ErrMsg.consent_policy_missing)
        should.contain(msg, t(AiConsent.SHARED_DATA_KEYWORD), ErrMsg.consent_data_missing)

        expect(
            dialog.container.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)),
            ErrMsg.button_not_visible,
        ).to_be_visible()


@allure.title("AI-согласие: отказ закрывает модалку и блокирует запрос")
def test_consent_decline_closes_modal_and_blocks_enrich_post(
    owner_page: Page,
    enrich_post_spy: list[str],
    pages: PageFactory,
) -> None:
    """TC-AI-1 (negative): Cancel в consent modal — modal закрывается, POST не уходит."""
    with step("подготовка: открыть профиль"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

    with step("действие: клик обогащения и отказ в consent"):
        panel.trigger_enrichment()
        dialog = pages.create(ConfirmDialog)
        dialog.expect_visible()
        dialog.click_button(t(AiConsent.DECLINE_LABEL))

    with step("проверка: модалка закрылась и POST не ушёл"):
        dialog.expect_hidden()
        should.be_empty(enrich_post_spy, ErrMsg.decline_should_block_post)


@allure.title("AI-согласие: повторный клик после отказа снова показывает модалку")
def test_consent_re_click_after_decline_re_renders_modal(owner_page: Page, pages: PageFactory) -> None:
    """Повторный click ★ после Decline снова показывает consent modal."""
    with step("подготовка: открыть профиль и отказаться от consent"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

        panel.trigger_enrichment()
        dialog = pages.create(ConfirmDialog)
        dialog.expect_visible()
        dialog.click_button(t(AiConsent.DECLINE_LABEL))
        dialog.expect_hidden()

    with step("проверка: повторный клик снова показывает consent modal"):
        panel.trigger_enrichment()
        pages.create(ConfirmDialog).expect_visible()
