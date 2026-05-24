"""TC-AI-1: GDPR/152-FZ consent dialog перед первым ★ Найти больше.

Контракт (`js/components/enrichment-modal.js:97-117`):

1. На первый клик «★ Найти больше» рендерится custom modal
   `confirmDialog()` (не native `confirm()`) с текстом про Anthropic
   Inc., перечнем передаваемых данных и ссылкой на политику.
2. Cancel → POST /api/enrich/{pid} НЕ улетает, modal закрывается.
3. Re-click «★» после decline → modal появляется снова
   (compliance: каждый click — новый opportunity to confirm consent;
    silent suppress = leak vector).

Тесты — pure user-flow: открыть profile, кликнуть звезду, прочитать
текст в DOM, нажать кнопку, проверить через DOM что modal закрыт и что
сеть не пошла. Без `evaluate('localStorage...')` для assertions.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests._core.messages import AiConsent, t
from tests._core.step import step
from tests.helpers.enrichment.enrichment_ui import consent_dialog, enrich_button, open_demo_self


@allure.title("AI-согласие: первый клик показывает модалку с Anthropic и политикой")
def test_first_enrich_click_renders_consent_modal_with_legal_content(
    owner_page: Page,
):
    """TC-AI-1 (positive): первый click ★ → modal с Anthropic + privacy
    policy + перечислением shared data."""
    with step("действие: открыть профиль и кликнуть обогащение"):
        open_demo_self(owner_page)
        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog).to_be_visible()

    with step("проверка: модалка содержит Anthropic, политику и shared data"):
        msg = dialog.inner_text()
        assert AiConsent.PROVIDER in msg, (
            f"consent text must mention {AiConsent.PROVIDER!r}; got: {msg[:200]!r}"
        )
        assert t(AiConsent.POLICY_KEYWORD) in msg.lower(), (
            f"consent text must reference privacy policy ({t(AiConsent.POLICY_KEYWORD)!r}); "
            f"got: {msg[:200]!r}"
        )
        assert t(AiConsent.SHARED_DATA_KEYWORD) in msg, (
            f"consent text must list what data is sent ({t(AiConsent.SHARED_DATA_KEYWORD)!r}); "
            f"got: {msg[:200]!r}"
        )

        # Кнопки видны (positive UI-contract — пользователь имеет выбор).
        expect(dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL))).to_be_visible()


@allure.title("AI-согласие: отказ закрывает модалку и блокирует запрос")
def test_consent_decline_closes_modal_and_blocks_enrich_post(owner_page: Page):
    """TC-AI-1 (negative): Cancel в consent modal — modal закрывается, и
    POST /api/enrich/* не уходит ни до, ни после клика.

    Это compliance-критичный invariant: даже при ошибочном клике
    «★ Найти больше» данные карточки НЕ уходят к Anthropic, пока
    пользователь не принял консент явно.
    """
    with step("подготовка: открыть профиль и подписаться на POST /api/enrich/"):
        open_demo_self(owner_page)

        enrich_posts: list[str] = []
        owner_page.on(
            "request",
            lambda req: enrich_posts.append(req.url)
            if req.method == "POST" and "/api/enrich/" in req.url
            else None,
        )

    with step("действие: клик обогащения и отказ в consent"):
        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()

    with step("проверка: модалка закрылась и POST не ушёл"):
        # Modal закрылся — user-visible signal что decline принят.
        expect(dialog).not_to_be_visible()

        # Сеть не пошла на enrichment.
        assert enrich_posts == [], (
            f"declined consent must not trigger POST /api/enrich/*; got: {enrich_posts}"
        )


@allure.title("AI-согласие: повторный клик после отказа снова показывает модалку")
def test_consent_re_click_after_decline_re_renders_modal(owner_page: Page):
    """Compliance: second click «★» **после** Decline должен снова показать
    consent modal — не silent fail (тогда юзер не знает что enrich
    выключен) и не silent send (compliance leak).
    """
    with step("подготовка: открыть профиль и отказаться от consent"):
        open_demo_self(owner_page)

        # First click + decline.
        enrich_button(owner_page).click()
        dialog = consent_dialog(owner_page)
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()
        expect(dialog).not_to_be_visible()

    with step("проверка: повторный клик снова показывает consent modal"):
        # Second click → modal должен снова появиться (или дать понятный
        # «cooldown» сигнал; main contract — НЕ silent fail).
        enrich_button(owner_page).click()
        expect(consent_dialog(owner_page)).to_be_visible()
