"""TC-AI-1: GDPR/152-FZ consent dialog перед первым ★ Найти больше."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.step import step
from helpers.enrichment.enrichment_ui import consent_dialog, enrich_button, open_demo_self
from src.texts import AiConsent, ErrMsg, t


@allure.title("AI-согласие: первый клик показывает модалку с Anthropic и политикой")
def test_first_enrich_click_renders_consent_modal_with_legal_content(
    owner_page: Page,
) -> None:
    """TC-AI-1 (positive): первый click ★ → modal с Anthropic + privacy policy."""
    with step("действие: открыть профиль и кликнуть обогащение"):
        open_demo_self(owner_page)
        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog, ErrMsg.dialog_not_visible).to_be_visible()

    with step("проверка: модалка содержит Anthropic, политику и shared data"):
        msg = dialog.inner_text()
        should.contain(msg, AiConsent.PROVIDER, ErrMsg.consent_provider_missing)
        should.contain(msg.lower(), t(AiConsent.POLICY_KEYWORD), ErrMsg.consent_policy_missing)
        should.contain(msg, t(AiConsent.SHARED_DATA_KEYWORD), ErrMsg.consent_data_missing)

        expect(dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)), ErrMsg.button_not_visible).to_be_visible()


@allure.title("AI-согласие: отказ закрывает модалку и блокирует запрос")
def test_consent_decline_closes_modal_and_blocks_enrich_post(owner_page: Page) -> None:
    """TC-AI-1 (negative): Cancel в consent modal — modal закрывается, POST не уходит."""
    with step("подготовка: открыть профиль и подписаться на POST /api/enrich/"):
        open_demo_self(owner_page)

        enrich_posts: list[str] = []
        owner_page.on(
            "request",
            lambda req: enrich_posts.append(req.url)
            if req.method == "POST" and routes.ENRICH_PREFIX in req.url
            else None,
        )

    with step("действие: клик обогащения и отказ в consent"):
        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog, ErrMsg.dialog_not_visible).to_be_visible()
        dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()

    with step("проверка: модалка закрылась и POST не ушёл"):
        expect(dialog, ErrMsg.dialog_should_be_closed).not_to_be_visible()
        should.be_empty(enrich_posts, ErrMsg.decline_should_block_post)


@allure.title("AI-согласие: повторный клик после отказа снова показывает модалку")
def test_consent_re_click_after_decline_re_renders_modal(owner_page: Page) -> None:
    """Повторный click ★ после Decline снова показывает consent modal."""
    with step("подготовка: открыть профиль и отказаться от consent"):
        open_demo_self(owner_page)

        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog, ErrMsg.dialog_not_visible).to_be_visible()
        dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()
        expect(dialog, ErrMsg.dialog_should_be_closed).not_to_be_visible()

    with step("проверка: повторный клик снова показывает consent modal"):
        enrich_button(owner_page).click()
        expect(consent_dialog(owner_page), ErrMsg.dialog_not_visible).to_be_visible()
