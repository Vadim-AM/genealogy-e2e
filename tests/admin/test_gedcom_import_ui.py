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

from http import HTTPStatus

import allure
from playwright.sync_api import Page, expect

from tests._core import api_paths as routes
from tests._core.err_msg import ErrMsg
from tests._core.messages import GedcomImport, t
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests._data.gedcom.samples import (
    SAMPLE_GEDCOM_CP1251,
    SAMPLE_GEDCOM_MALFORMED,
    SAMPLE_GEDCOM_UTF8,
)
from tests.helpers.admin.gedcom_ui import open_import_tab
from tests.helpers.tree.tree_api import people_count

# ─────────────────────────────────────────────────────────────────────────
# Основной сценарий (happy path)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("GEDCOM: экспорт дерева и повторный импорт идемпотентен")
def test_round_trip_export_then_import(owner_page: Page, owner_user, tenant_client):
    """Round-trip: export текущего seed-tree → upload его обратно через UI
    → preview → confirm → DONE summary показывает «Пропущено N» (т.к. вся
    база уже в БД, и backend идемпотентно скипает дубликаты по id).

    Was xfail until upstream backend fix for BUG-GEDCOM-001 (export-endpoint
    теперь кладёт display_slug в people_dicts, confirm-handler матчит
    existing person'ов по slug — count_after == count_before).
    """
    with step("подготовка: экспорт текущего дерева через API"):
        api = tenant_client(owner_user)
        # 1. Экспорт текущего дерева через API (возвращает .ged текстом)
        r = api.get(routes.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)
        assert r.is_success, f"export GEDCOM failed: {r.status_code} {r.text[:200]}"
        ged_text = r.text
        assert "0 HEAD" in ged_text[:100], f"exported GEDCOM missing header: {ged_text[:100]!r}"
        count_before = people_count(api)

    with step("действие: upload экспортированного файла обратно через UI"):
        # 2. Открываем /owner → вкладка «Импорт/Экспорт» → загружаем экспортированный файл обратно
        owner = open_import_tab(owner_page)
        owner.upload_ged(filename="round-trip.ged", content=ged_text.encode("utf-8"))

        # 3. Состояние preview — счётчики видимы
        owner.expect_import_state("PREVIEW")
        expect(owner.import_stats, ErrMsg.gedcom_stats_not_visible).to_be_visible()
        expect(owner.import_confirm_btn, ErrMsg.button_not_visible).to_be_visible()

        # 4. Подтверждение через confirmDialog
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")

    with step("проверка: DONE показывает «Пропущено» и count не изменился"):
        # 5. DONE-сводка содержит «Пропущено» — нет реально-новых persons
        summary_text = owner.import_summary.text_content() or ""
        assert t(GedcomImport.SKIPPED_LABEL) in summary_text, f"expected skipped count in DONE: {summary_text!r}"

        # API: count не изменился — backend пропустил всех (idempotent)
        count_after = people_count(api)
        assert count_after == count_before, (
            f"round-trip leaked new persons: before={count_before}, after={count_after}"
        )


@allure.title("GEDCOM: импортированные персоны появляются в дереве")
def test_import_new_persons_visible_in_tree(owner_page: Page, owner_user, tenant_client):
    """Fresh sample.ged → preview → confirm → assert новые persons в /api/tree."""
    with step("подготовка: запомнить count до импорта"):
        api = tenant_client(owner_user)
        count_before = people_count(api)

    with step("действие: upload и confirm нового GEDCOM"):
        owner = open_import_tab(owner_page)
        owner.upload_ged(filename="fresh.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.expect_import_state("PREVIEW")
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")

    with step("проверка: новые персоны появились в /api/tree"):
        api = tenant_client(owner_user)
        tree_after = api.get(routes.TREE).json()
        assert len(tree_after["people"]) >= count_before + 2, (
            f"expected ≥2 new persons; before={count_before}, after={len(tree_after['people'])}"
        )
        names = {p["name"] for p in tree_after["people"]}
        assert any("Импортов" in n for n in names), f"new person not in tree: {names}"


# ─────────────────────────────────────────────────────────────────────────
# Encoding (РФ-критичный)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("GEDCOM: импорт CP1251 корректно отображает кириллицу")
def test_cp1251_shows_cyrillic_correctly(owner_page: Page, owner_user):
    """Файл в Windows-1251 → preview показывает badge cp1251 + кириллица
    читается корректно (не mojibake). Главный РФ-кейс Фазы 2 — юзеры
    таскают .ged из «Древо Жизни» в этой кодировке."""
    with step("действие: upload CP1251 файла"):
        owner = open_import_tab(owner_page)
        owner.upload_ged(
            filename="cp1251.ged",
            content=SAMPLE_GEDCOM_CP1251.encode("cp1251"),
        )
        owner.expect_import_state("PREVIEW")

    with step("проверка: encoding badge и кириллица без mojibake"):
        # Бейдж кодировки показывает "cp1251"
        expect(
            owner.import_encoding_badge, ErrMsg.gedcom_encoding_wrong,
        ).to_have_attribute("data-gedcom-encoding", "cp1251")
        expect(owner.import_encoding_badge, ErrMsg.gedcom_encoding_wrong).to_contain_text("Windows-1251")
        # Список preview (раскрываемый details) содержит кириллическое имя — ловит mojibake
        expect(owner.import_root, ErrMsg.wrong_text_content).to_contain_text("Иван")
        expect(owner.import_root, ErrMsg.wrong_text_content).to_contain_text("Кириллов")


@allure.title("GEDCOM: UTF-8 файл показывает нейтральный encoding badge")
def test_utf8_encoding_badge_is_neutral(owner_page: Page, owner_user):
    """UTF-8 файл → encoding badge тоже есть (для прозрачности), но
    нейтральный (без ⚠), data-gedcom-encoding=utf-8."""
    owner = open_import_tab(owner_page)
    owner.upload_ged(filename="utf8.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    expect(owner.import_encoding_badge, ErrMsg.gedcom_encoding_wrong).to_have_attribute("data-gedcom-encoding", "utf-8")


# ─────────────────────────────────────────────────────────────────────────
# Стейт-машина
# ─────────────────────────────────────────────────────────────────────────


@allure.title("GEDCOM: отмена на этапе превью сбрасывает в IDLE")
def test_cancel_during_preview_resets_to_idle(owner_page: Page, owner_user, tenant_client):
    """Upload → PREVIEW → click Cancel → IDLE. Никаких persons не записано."""
    with step("подготовка: запомнить count и upload файла"):
        api = tenant_client(owner_user)
        count_before = people_count(api)
        owner = open_import_tab(owner_page)
        owner.upload_ged(filename="cancel.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.expect_import_state("PREVIEW")

    with step("действие: отмена на этапе preview"):
        owner.import_cancel_btn.click()
        owner.expect_import_state("IDLE")

    with step("проверка: count не изменился"):
        count_after = people_count(api)
        assert count_after == count_before, (
            f"cancel leaked persons: before={count_before}, after={count_after}"
        )


@allure.title("GEDCOM: отмена в диалоге подтверждения не импортирует данные")
def test_confirm_dialog_cancel_blocks_import(owner_page: Page, owner_user, tenant_client):
    """Click Confirm → confirmDialog opens → click Отмена в dialog →
    остаёмся в PREVIEW, никаких записей в БД."""
    with step("подготовка: upload файла до PREVIEW"):
        api = tenant_client(owner_user)
        count_before = people_count(api)
        owner = open_import_tab(owner_page)
        owner.upload_ged(filename="block.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.expect_import_state("PREVIEW")

    with step("действие: открыть confirmDialog и нажать Отмена"):
        # Кликаем Confirm виджета — confirmDialog появляется на body
        owner.import_confirm_btn.click()
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        # Кликаем Отмена в dialog — должен закрыть dialog, оставить в PREVIEW
        owner.confirm_dialog_cancel.click()
        expect(owner.confirm_dialog, ErrMsg.dialog_should_be_closed).to_have_count(0)
        owner.expect_import_state("PREVIEW")

    with step("проверка: count не изменился после отмены"):
        count_after = people_count(api)
        assert count_after == count_before, (
            f"cancel must not import: before={count_before}, after={count_after}"
        )


@allure.title("GEDCOM: повторный импорт показывает счётчик пропущенных")
def test_done_shows_skipped_count_on_reimport(owner_page: Page, owner_user, tenant_client):
    """Двойной импорт того же файла → DONE второго показывает «Пропущено»
    (не «Импорт упал»), счётчик правильный."""
    with step("подготовка: первый импорт файла"):
        owner = open_import_tab(owner_page)
        owner.upload_ged(filename="first.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")
        # Сброс через «Импортировать ещё файл»
        owner.import_again_btn.click()
        owner.expect_import_state("IDLE")

    with step("действие: повторный импорт того же файла"):
        owner.upload_ged(filename="second.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")

    with step("проверка: DONE summary содержит «Пропущено»"):
        summary_text = owner.import_summary.text_content() or ""
        assert t(GedcomImport.SKIPPED_LABEL) in summary_text, summary_text


@allure.title("GEDCOM: после ошибки сервера Retry сбрасывает в IDLE")
def test_retry_after_error_resets_to_idle(owner_page: Page, owner_user):
    """ERROR state → click Retry → IDLE (state-machine reset)."""
    with step("подготовка: перехват POST и вызов ошибки 500"):
        owner = open_import_tab(owner_page)
        # Перехватываем POST /import-gedcom и возвращаем 500
        def _block_500(route):
            if route.request.method == "POST":
                route.fulfill(status=HTTPStatus.INTERNAL_SERVER_ERROR, body='{"detail":"server boom"}',
                              content_type="application/json")
            else:
                route.continue_()
        owner_page.route(f"**{routes.ADMIN_IMPORT_GEDCOM}", _block_500)
        try:
            owner.upload_ged(filename="boom.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
            owner.expect_import_state("ERROR")
            expect(owner.import_error, ErrMsg.gedcom_import_state_wrong).to_be_visible()
        finally:
            owner_page.unroute(f"**{routes.ADMIN_IMPORT_GEDCOM}")

    with step("проверка: Retry сбрасывает в IDLE"):
        owner.import_retry_btn.click()
        owner.expect_import_state("IDLE")


# ─────────────────────────────────────────────────────────────────────────
# Негативные сценарии (клиентская валидация)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("GEDCOM: загрузка .txt файла отклоняется без отправки")
def test_rejects_non_ged_extension(owner_page: Page, owner_user):
    """Upload .txt файла → alertDialog (sepia, не native browser alert),
    POST не делается."""
    with step("подготовка: открыть вкладку импорта и установить слушатель"):
        owner = open_import_tab(owner_page)
        posted: list[str] = []
        owner_page.on("request", lambda req:
                      posted.append(req.url) if req.method == "POST"
                      and "/import-gedcom" in req.url else None)

    with step("действие: загрузить .txt файл"):
        owner.import_file_input.set_input_files(
            files=[{"name": "notgedcom.txt", "mimeType": "text/plain", "buffer": b"hello"}]  # type: ignore[arg-type]
        )

    with step("проверка: alertDialog появился и POST не отправлен"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(GedcomImport.FILE_EXTENSION_HINT)
        assert posted == [], f"unexpected POSTs: {posted}"
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")


@allure.title("GEDCOM: пустой .ged файл отклоняется с предупреждением")
def test_rejects_empty_file(owner_page: Page, owner_user):
    """0-byte .ged → alertDialog «пустой», без POST."""
    with step("действие: загрузить пустой .ged файл"):
        owner = open_import_tab(owner_page)
        owner.import_file_input.set_input_files(
            files=[{"name": "empty.ged", "mimeType": "application/octet-stream", "buffer": b""}]  # type: ignore[arg-type]
        )

    with step("проверка: alertDialog «пустой» и возврат в IDLE"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(t(GedcomImport.EMPTY_LABEL))
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")


@allure.title("GEDCOM: файл больше 10 МБ отклоняется на клиенте")
def test_rejects_oversize_file(owner_page: Page, owner_user):
    """11 MB .ged → client-side reject «слишком большой»."""
    with step("подготовка: создать payload >10 MB"):
        # `b"1 NOTE xx\n"` — ровно 10 байт, чтобы multiplier × 10 = bytes.
        big_payload = b"0 HEAD\n" + b"1 NOTE xx\n" * (11 * 1024 * 1024 // 10)
        assert len(big_payload) > 10 * 1024 * 1024, \
            f"sanity: payload must exceed 10 MB, got {len(big_payload)}"

    with step("действие: загрузить oversize файл"):
        owner = open_import_tab(owner_page)
        owner.import_file_input.set_input_files(
            files=[  # type: ignore[arg-type]
                {
                    "name": "huge.ged",
                    "mimeType": "application/octet-stream",
                    "buffer": big_payload,
                }
            ]
        )

    with step("проверка: alertDialog «слишком большой» и возврат в IDLE"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(t(GedcomImport.TOO_LARGE_LABEL))
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")


# ─────────────────────────────────────────────────────────────────────────
# Негативные сценарии (сервер / сеть)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("GEDCOM: ошибка 400 от бэкенда показывает detail в UI")
def test_backend_400_shows_friendly_error(owner_page: Page, owner_user):
    """Backend возвращает 400 с detail — UI показывает inline ERROR с этим detail."""
    with step("подготовка: перехват POST с ответом 400"):
        owner = open_import_tab(owner_page)

        def _block_400(route):
            if route.request.method == "POST":
                route.fulfill(
                    status=HTTPStatus.BAD_REQUEST,
                    body='{"detail":"GEDCOM parse error: line 5 unexpected token"}',
                    content_type="application/json",
                )
            else:
                route.continue_()

        owner_page.route(f"**{routes.ADMIN_IMPORT_GEDCOM}", _block_400)

    with step("проверка: UI показывает ERROR с detail от бэкенда"):
        try:
            owner.upload_ged(filename="malformed.ged", content=SAMPLE_GEDCOM_MALFORMED)
            owner.expect_import_state("ERROR")
            expect(owner.import_error, ErrMsg.wrong_text_content).to_contain_text("GEDCOM parse error")
        finally:
            owner_page.unroute(f"**{routes.ADMIN_IMPORT_GEDCOM}")


@allure.title("GEDCOM: обрыв сети показывает понятное сообщение об ошибке")
def test_network_error_shows_friendly_message(owner_page: Page, owner_user):
    """Полный network fail (route.abort) → ERROR с friendly message."""
    with step("подготовка: перехват POST с abort"):
        owner = open_import_tab(owner_page)
        owner_page.route(f"**{routes.ADMIN_IMPORT_GEDCOM}", lambda r: r.abort())

    with step("проверка: ERROR с friendly message"):
        try:
            owner.upload_ged(filename="fail.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
            owner.expect_import_state("ERROR")
            # Сообщение — понятное, не сырой stacktrace
            expect(owner.import_error, ErrMsg.gedcom_import_state_wrong).to_be_visible()
        finally:
            owner_page.unroute(f"**{routes.ADMIN_IMPORT_GEDCOM}")
