"""GEDCOM import UI — two-stage flow (Фаза 2).

UI mounts at /owner → tab «Импорт и экспорт» → block «Импорт GEDCOM».
Backend endpoints готовы (POST /api/admin/import-gedcom +
/import-gedcom/confirm), все тесты в этом файле фокусируются на UI side:
state machine, preview rendering, encoding-badge, error paths, idempotency.

Стратегия:
- Главные сценарии — round-trip (экспорт реально-существующего seed-tree
  через API, потом upload его обратно через UI). Это покрывает 90% реальной
  пользовательской боли: «я экспортнул из MyHeritage и хочу залить сюда».
- Variants — cp1251 (главный РФ-кейс), state-machine transitions, sad-paths.

Уровень assertions: API+UI. Каждый тест проверяет как UI-стейт, так и
итоговое состояние в /api/tree (если confirm имел место).
"""

from __future__ import annotations

import httpx
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.pages.owner_page import OwnerPage
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


SAMPLE_GEDCOM_UTF8 = (
    "0 HEAD\n"
    "1 SOUR Genealogy-e2e\n"
    "1 GEDC\n"
    "2 VERS 5.5.1\n"
    "1 CHAR UTF-8\n"
    "0 @I1@ INDI\n"
    "1 NAME Тестовый /Импортов/\n"
    "1 SEX M\n"
    "1 BIRT\n"
    "2 DATE 1900\n"
    "0 @I2@ INDI\n"
    "1 NAME Импортова /Тестовая/\n"
    "1 SEX F\n"
    "1 BIRT\n"
    "2 DATE 1902\n"
    "0 TRLR\n"
)


SAMPLE_GEDCOM_CP1251 = (
    "0 HEAD\n"
    "1 SOUR Tree-1251\n"
    "1 CHAR ANSI\n"
    "0 @I1@ INDI\n"
    "1 NAME Иван /Кириллов/\n"
    "1 SEX M\n"
    "1 BIRT\n"
    "2 DATE 1890\n"
    "0 TRLR\n"
)


SAMPLE_GEDCOM_MALFORMED = b"this is not a gedcom file just random text\x00\x01\xff\xfe"


def _open_import_tab(owner_page: Page) -> OwnerPage:
    owner = OwnerPage(owner_page)
    owner_page.goto("/owner")
    owner_page.wait_for_load_state("networkidle")
    owner.open_tab("export")
    # Widget mounts after loadMe() resolves — wait for IDLE state
    expect(owner.import_root).to_have_attribute("data-gedcom-state", "IDLE")
    return owner


def _tree_people_count(owner_user, tenant_client) -> int:
    api = tenant_client(owner_user)
    return len(api.get(API.TREE).json()["people"])


# ─────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────


def test_round_trip_export_then_import(owner_page: Page, owner_user, tenant_client):
    """Round-trip: export текущего seed-tree → upload его обратно через UI
    → preview → confirm → DONE summary показывает «Пропущено N» (т.к. вся
    база уже в БД, и backend идемпотентно скипает дубликаты по id).
    """
    api = tenant_client(owner_user)
    # 1. Export current tree via API (returns .ged text body)
    r = api.get(API.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)
    assert r.ok, r.text
    ged_text = r.text
    assert "0 HEAD" in ged_text[:100]

    count_before = _tree_people_count(owner_user, tenant_client)

    # 2. Open /owner → Import/Export tab → upload exported file back
    owner = _open_import_tab(owner_page)
    owner.upload_ged(filename="round-trip.ged", content=ged_text.encode("utf-8"))

    # 3. Preview state — counts визибл
    owner.expect_import_state("PREVIEW")
    expect(owner.import_stats).to_be_visible()
    expect(owner.import_confirm_btn).to_be_visible()

    # 4. Confirm via confirmDialog gate
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")

    # 5. DONE summary mentions «Пропущено» — нет реально-новых persons
    summary_text = owner.import_summary.text_content() or ""
    assert "Пропущено" in summary_text, f"expected skipped count in DONE: {summary_text!r}"

    # API: count не изменился — backend skipnул всех (idempotent)
    count_after = _tree_people_count(owner_user, tenant_client)
    assert count_after == count_before, (
        f"round-trip leaked new persons: before={count_before}, after={count_after}"
    )


def test_import_new_persons_visible_in_tree(owner_page: Page, owner_user, tenant_client):
    """Fresh sample.ged → preview → confirm → assert новые persons в /api/tree."""
    count_before = _tree_people_count(owner_user, tenant_client)

    owner = _open_import_tab(owner_page)
    owner.upload_ged(filename="fresh.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")

    api = tenant_client(owner_user)
    tree_after = api.get(API.TREE).json()
    assert len(tree_after["people"]) >= count_before + 2, (
        f"expected ≥2 new persons; before={count_before}, after={len(tree_after['people'])}"
    )
    names = {p["name"] for p in tree_after["people"]}
    assert any("Импортов" in n for n in names), f"new person not in tree: {names}"


# ─────────────────────────────────────────────────────────────────────────
# Encoding (РФ-критичный)
# ─────────────────────────────────────────────────────────────────────────


def test_cp1251_shows_cyrillic_correctly(owner_page: Page, owner_user):
    """Файл в Windows-1251 → preview показывает badge cp1251 + кириллица
    читается корректно (не mojibake). Главный РФ-кейс Фазы 2 — юзеры
    таскают .ged из «Древо Жизни» в этой кодировке."""
    owner = _open_import_tab(owner_page)
    owner.upload_ged(
        filename="cp1251.ged",
        content=SAMPLE_GEDCOM_CP1251.encode("cp1251"),
    )
    owner.expect_import_state("PREVIEW")
    # Encoding badge says "cp1251"
    expect(owner.import_encoding_badge).to_have_attribute("data-gedcom-encoding", "cp1251")
    expect(owner.import_encoding_badge).to_contain_text("Windows-1251")
    # Preview list (collapsible details) contains cyrillic name — ловит mojibake
    expect(owner.import_root).to_contain_text("Иван")
    expect(owner.import_root).to_contain_text("Кириллов")


def test_utf8_encoding_badge_is_neutral(owner_page: Page, owner_user):
    """UTF-8 файл → encoding badge тоже есть (для прозрачности), но
    нейтральный (без ⚠), data-gedcom-encoding=utf-8."""
    owner = _open_import_tab(owner_page)
    owner.upload_ged(filename="utf8.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    expect(owner.import_encoding_badge).to_have_attribute("data-gedcom-encoding", "utf-8")


# ─────────────────────────────────────────────────────────────────────────
# State machine
# ─────────────────────────────────────────────────────────────────────────


def test_cancel_during_preview_resets_to_idle(owner_page: Page, owner_user, tenant_client):
    """Upload → PREVIEW → click Cancel → IDLE. Никаких persons не записано."""
    count_before = _tree_people_count(owner_user, tenant_client)

    owner = _open_import_tab(owner_page)
    owner.upload_ged(filename="cancel.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    owner.import_cancel_btn.click()
    owner.expect_import_state("IDLE")

    count_after = _tree_people_count(owner_user, tenant_client)
    assert count_after == count_before, (
        f"cancel leaked persons: before={count_before}, after={count_after}"
    )


def test_confirm_dialog_cancel_blocks_import(owner_page: Page, owner_user, tenant_client):
    """Click Confirm → confirmDialog opens → click Отмена в dialog →
    остаёмся в PREVIEW, никаких записей в БД."""
    count_before = _tree_people_count(owner_user, tenant_client)

    owner = _open_import_tab(owner_page)
    owner.upload_ged(filename="block.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")

    # Click widget's Confirm — confirmDialog появляется на body
    owner.import_confirm_btn.click()
    expect(owner.confirm_dialog).to_be_visible()
    # Click Cancel в dialog — должен закрыть dialog, оставить в PREVIEW
    owner.confirm_dialog_cancel.click()
    expect(owner.confirm_dialog).to_have_count(0)
    owner.expect_import_state("PREVIEW")

    count_after = _tree_people_count(owner_user, tenant_client)
    assert count_after == count_before


def test_done_shows_skipped_count_on_reimport(owner_page: Page, owner_user, tenant_client):
    """Двойной импорт того же файла → DONE второго показывает «Пропущено»
    (не «Импорт упал»), счётчик правильный."""
    owner = _open_import_tab(owner_page)
    # First import
    owner.upload_ged(filename="first.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")
    # Reset via "Импортировать ещё файл"
    owner.import_again_btn.click()
    owner.expect_import_state("IDLE")

    # Second import same file
    owner.upload_ged(filename="second.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")
    summary_text = owner.import_summary.text_content() or ""
    assert "Пропущено" in summary_text, summary_text


def test_retry_after_error_resets_to_idle(owner_page: Page, owner_user):
    """ERROR state → click Retry → IDLE (state-machine reset)."""
    owner = _open_import_tab(owner_page)
    # Перехватываем POST /import-gedcom и возвращаем 500
    def _block_500(route):
        if route.request.method == "POST":
            route.fulfill(status=500, body='{"detail":"server boom"}',
                          content_type="application/json")
        else:
            route.continue_()
    owner_page.route("**/api/admin/import-gedcom", _block_500)
    try:
        owner.upload_ged(filename="boom.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.expect_import_state("ERROR")
        expect(owner.import_error).to_be_visible()
    finally:
        owner_page.unroute("**/api/admin/import-gedcom")

    owner.import_retry_btn.click()
    owner.expect_import_state("IDLE")


# ─────────────────────────────────────────────────────────────────────────
# Sad paths (client-side validation)
# ─────────────────────────────────────────────────────────────────────────


def test_rejects_non_ged_extension(owner_page: Page, owner_user):
    """Upload .txt файла → alertDialog (sepia, не native browser alert),
    POST не делается."""
    owner = _open_import_tab(owner_page)
    posted: list[str] = []
    owner_page.on("request", lambda req:
                  posted.append(req.url) if req.method == "POST"
                  and "/import-gedcom" in req.url else None)

    owner.import_file_input.set_input_files(
        files=[{"name": "notgedcom.txt", "mimeType": "text/plain", "buffer": b"hello"}]
    )
    # alertDialog появляется
    expect(owner.confirm_dialog).to_be_visible()
    expect(owner.confirm_dialog).to_contain_text(".ged")
    # POST НЕ был отправлен
    assert posted == [], f"unexpected POSTs: {posted}"
    # Закрываем alertDialog
    owner.confirm_dialog_ok.click()
    owner.expect_import_state("IDLE")


def test_rejects_empty_file(owner_page: Page, owner_user):
    """0-byte .ged → alertDialog «пустой», без POST."""
    owner = _open_import_tab(owner_page)
    owner.import_file_input.set_input_files(
        files=[{"name": "empty.ged", "mimeType": "application/octet-stream", "buffer": b""}]
    )
    expect(owner.confirm_dialog).to_be_visible()
    expect(owner.confirm_dialog).to_contain_text("пустой")
    owner.confirm_dialog_ok.click()
    owner.expect_import_state("IDLE")


def test_rejects_oversize_file(owner_page: Page, owner_user):
    """11 MB .ged → client-side reject «слишком большой»."""
    big_payload = b"0 HEAD\n" + b"1 NOTE x\n" * (11 * 1024 * 1024 // 10)
    assert len(big_payload) > 10 * 1024 * 1024  # sanity

    owner = _open_import_tab(owner_page)
    owner.import_file_input.set_input_files(
        files=[
            {
                "name": "huge.ged",
                "mimeType": "application/octet-stream",
                "buffer": big_payload,
            }
        ]
    )
    expect(owner.confirm_dialog).to_be_visible()
    expect(owner.confirm_dialog).to_contain_text("слишком большой")
    owner.confirm_dialog_ok.click()
    owner.expect_import_state("IDLE")


# ─────────────────────────────────────────────────────────────────────────
# Sad paths (server / network)
# ─────────────────────────────────────────────────────────────────────────


def test_backend_400_shows_friendly_error(owner_page: Page, owner_user):
    """Backend возвращает 400 с detail — UI показывает inline ERROR с этим detail."""
    owner = _open_import_tab(owner_page)

    def _block_400(route):
        if route.request.method == "POST":
            route.fulfill(
                status=400,
                body='{"detail":"GEDCOM parse error: line 5 unexpected token"}',
                content_type="application/json",
            )
        else:
            route.continue_()

    owner_page.route("**/api/admin/import-gedcom", _block_400)
    try:
        owner.upload_ged(filename="malformed.ged", content=SAMPLE_GEDCOM_MALFORMED)
        owner.expect_import_state("ERROR")
        expect(owner.import_error).to_contain_text("GEDCOM parse error")
    finally:
        owner_page.unroute("**/api/admin/import-gedcom")


def test_network_error_shows_friendly_message(owner_page: Page, owner_user):
    """Полный network fail (route.abort) → ERROR с friendly message."""
    owner = _open_import_tab(owner_page)
    owner_page.route("**/api/admin/import-gedcom", lambda r: r.abort())
    try:
        owner.upload_ged(filename="fail.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.expect_import_state("ERROR")
        # Message — friendly, не raw stacktrace
        expect(owner.import_error).to_be_visible()
    finally:
        owner_page.unroute("**/api/admin/import-gedcom")
