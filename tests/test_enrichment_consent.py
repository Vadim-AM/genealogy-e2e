"""TC-AI-1: GDPR/152-FZ consent confirm() перед первым ★ Найти больше.

Контракт (`js/components/enrichment-modal.js:97-117`):

1. На первый клик «★ Найти больше» проверяется
   `localStorage.genealogy_ai_consent_v1`. Если нет — рендерится
   нативный `confirm()` с текстом про Anthropic Inc., перечнем
   передаваемых данных и ссылкой на политику конфиденциальности.
2. Cancel → НИ ОДНОГО POST на `/api/enrich/{pid}` не уходит,
   `genealogy_ai_decline_count` инкрементится.
3. Accept → `genealogy_ai_consent_v1` сохраняется + best-effort
   POST `/api/account/me/ai-consent` для legal-record (ст. 9 ч. 1
   ФЗ-152 / GDPR ст. 7 — нужен доказуемый active consent).

Эти тесты гарантируют, что консент-гейт не обходится «случайно»
(например, refactor'ом флоу или сменой условий) — это П0
compliance regression.
"""

from __future__ import annotations

from playwright.sync_api import Page

from tests.messages import AiConsent, TestData, t


_CONSENT_LOCALSTORAGE_KEYS = (
    "genealogy_ai_consent_v1",
    "genealogy_ai_dismissed_until",
    "genealogy_ai_decline_count",
)


def _clear_consent_state(page: Page) -> None:
    """Wipe consent flags so the next ★-click triggers the dialog.

    `auth_context_factory` pre-seeds tour flags but не consent — однако
    при повторном использовании контекста (или при необычной cookie-
    среде) флаг мог остаться. Очищаем явно.
    """
    page.evaluate(
        "(keys) => keys.forEach((k) => localStorage.removeItem(k))",
        list(_CONSENT_LOCALSTORAGE_KEYS),
    )


def _open_demo_self(page: Page) -> None:
    page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    page.wait_for_load_state("networkidle")


def test_first_enrich_click_shows_consent_with_anthropic_and_policy_link(
    owner_page: Page,
):
    """TC-AI-1 (positive): consent confirm содержит legal-load (Anthropic + политика)."""
    _open_demo_self(owner_page)
    _clear_consent_state(owner_page)

    captured = {}

    def on_dialog(d):
        captured["type"] = d.type
        captured["message"] = d.message
        d.dismiss()

    owner_page.on("dialog", on_dialog)
    owner_page.get_by_role("button", name="Найти больше", exact=False).click()

    # Декрементер `decline_count` пишется СИНХРОННО после dismiss — это
    # deterministic gate, что dialog handler отработал.
    owner_page.wait_for_function(
        "() => parseInt(localStorage.getItem('genealogy_ai_decline_count') || '0', 10) >= 1",
        timeout=5_000,
    )

    assert captured.get("type") == "confirm", (
        f"expected confirm() dialog, got type={captured.get('type')!r}"
    )
    msg = captured.get("message") or ""
    assert AiConsent.PROVIDER in msg, (
        f"consent text must mention {AiConsent.PROVIDER!r}; got: {msg[:200]!r}"
    )
    assert t(AiConsent.POLICY_KEYWORD) in msg.lower() or t(AiConsent.POLICY_KEYWORD) in msg, (
        f"consent text must reference privacy policy ({t(AiConsent.POLICY_KEYWORD)!r}); "
        f"got: {msg[:200]!r}"
    )
    assert t(AiConsent.SHARED_DATA_KEYWORD) in msg, (
        f"consent text must list what data is sent ({t(AiConsent.SHARED_DATA_KEYWORD)!r}); "
        f"got: {msg[:200]!r}"
    )


def test_consent_decline_blocks_post_to_enrich_endpoint(owner_page: Page):
    """TC-AI-1 (negative): cancel в consent dialog → POST /api/enrich/* не уходит.

    Это compliance-критичный invariant: даже при ошибочном клике
    «★ Найти больше» данные карточки НЕ уходят к Anthropic, пока
    пользователь не принял консент явно.
    """
    _open_demo_self(owner_page)
    _clear_consent_state(owner_page)

    enrich_posts: list[str] = []

    def track_request(req):
        if req.method == "POST" and "/api/enrich/" in req.url:
            enrich_posts.append(req.url)

    owner_page.on("request", track_request)
    owner_page.on("dialog", lambda d: d.dismiss())

    owner_page.get_by_role("button", name="Найти больше", exact=False).click()

    # Дождаться что handler отработал (decline_count→1) — после этого
    # ранний return гарантирован, новых POST'ов не будет.
    owner_page.wait_for_function(
        "() => parseInt(localStorage.getItem('genealogy_ai_decline_count') || '0', 10) >= 1",
        timeout=5_000,
    )

    assert enrich_posts == [], (
        f"declined consent must not trigger POST /api/enrich/*; got: {enrich_posts}"
    )
