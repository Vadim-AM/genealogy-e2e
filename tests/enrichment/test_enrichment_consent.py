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

from playwright.sync_api import Page, expect

from tests.messages import AiConsent, Buttons, TestData, t


def _open_demo_self(page: Page) -> None:
    page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    page.wait_for_load_state("domcontentloaded")


def _enrich_button(page: Page):
    return page.get_by_role("button", name=t(Buttons.ENRICH), exact=False)


def _consent_dialog(page: Page):
    return page.locator(".confirm-dialog").first


def test_first_enrich_click_renders_consent_modal_with_legal_content(
    owner_page: Page,
):
    """TC-AI-1 (positive): первый click ★ → modal с Anthropic + privacy
    policy + перечислением shared data."""
    _open_demo_self(owner_page)

    _enrich_button(owner_page).click()
    dialog = _consent_dialog(owner_page)
    expect(dialog).to_be_visible()

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


def test_consent_decline_closes_modal_and_blocks_enrich_post(owner_page: Page):
    """TC-AI-1 (negative): Cancel в consent modal — modal закрывается, и
    POST /api/enrich/* не уходит ни до, ни после клика.

    Это compliance-критичный invariant: даже при ошибочном клике
    «★ Найти больше» данные карточки НЕ уходят к Anthropic, пока
    пользователь не принял консент явно.
    """
    _open_demo_self(owner_page)

    enrich_posts: list[str] = []
    owner_page.on(
        "request",
        lambda req: enrich_posts.append(req.url)
        if req.method == "POST" and "/api/enrich/" in req.url
        else None,
    )

    _enrich_button(owner_page).click()
    dialog = _consent_dialog(owner_page)
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()

    # Modal закрылся — user-visible signal что decline принят.
    expect(dialog).not_to_be_visible()

    # Сеть не пошла на enrichment.
    assert enrich_posts == [], (
        f"declined consent must not trigger POST /api/enrich/*; got: {enrich_posts}"
    )


def test_consent_re_click_after_decline_re_renders_modal(owner_page: Page):
    """Compliance: second click «★» **после** Decline должен снова показать
    consent modal — не silent fail (тогда юзер не знает что enrich
    выключен) и не silent send (compliance leak).
    """
    _open_demo_self(owner_page)

    # First click + decline.
    _enrich_button(owner_page).click()
    dialog = _consent_dialog(owner_page)
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name=t(AiConsent.DECLINE_LABEL)).click()
    expect(dialog).not_to_be_visible()

    # Second click → modal должен снова появиться (или дать понятный
    # «cooldown» сигнал; main contract — НЕ silent fail).
    _enrich_button(owner_page).click()
    expect(_consent_dialog(owner_page)).to_be_visible()
