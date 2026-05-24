"""GEDCOM import UI: state machine, encoding, round-trip, error paths."""

from __future__ import annotations

from http import HTTPStatus

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from config.timeouts import TIMEOUTS
from framework.step import step
from helpers.admin.gedcom_ui import open_import_tab
from helpers.tree.tree_api import people_count
from src.texts import ErrMsg, GedcomImport, t
from test_data.gedcom.samples import (
    SAMPLE_GEDCOM_CP1251,
    SAMPLE_GEDCOM_MALFORMED,
    SAMPLE_GEDCOM_UTF8,
)


@allure.title("GEDCOM: экспорт дерева и повторный импорт идемпотентен")
def test_round_trip_export_then_import(owner_page: Page, owner_user, tenant_client) -> None:
    """Export seed-tree → re-import → DONE показывает «Пропущено», count не вырос."""
    with step("подготовка: экспорт текущего дерева через API"):
        api = tenant_client(owner_user)
        # 1. Экспорт текущего дерева через API (возвращает .ged текстом)
        r = api.get(routes.ADMIN_EXPORT_GEDCOM, timeout=TIMEOUTS.api_long)
        should.be_true(r.is_success, ErrMsg.gedcom_export_failed)
        ged_text = r.text
        should.contain(ged_text[:100], "0 HEAD", ErrMsg.gedcom_header_missing)
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
        should.contain(summary_text, t(GedcomImport.SKIPPED_LABEL), ErrMsg.gedcom_skipped_missing)

        count_after = people_count(api)
        should.be_equal(count_after, count_before, ErrMsg.gedcom_round_trip_leaked)


@allure.title("GEDCOM: импортированные персоны появляются в дереве")
def test_import_new_persons_visible_in_tree(owner_page: Page, owner_user, tenant_client) -> None:
    """Импорт нового GEDCOM добавляет persons в дерево."""
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
        should.greater_or_equal(len(tree_after["people"]), count_before + 2, ErrMsg.tree_count_wrong)
        names = {p["name"] for p in tree_after["people"]}
        should.any_match(names, lambda n: "Импортов" in n, ErrMsg.gedcom_new_person_missing)



@allure.title("GEDCOM: импорт CP1251 корректно отображает кириллицу")
def test_cp1251_shows_cyrillic_correctly(owner_page: Page, owner_user) -> None:
    """CP1251 файл показывает badge и кириллицу без mojibake."""
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
def test_utf8_encoding_badge_is_neutral(owner_page: Page, owner_user) -> None:
    """UTF-8 файл показывает нейтральный encoding badge."""
    owner = open_import_tab(owner_page)
    owner.upload_ged(filename="utf8.ged", content=SAMPLE_GEDCOM_UTF8.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    expect(owner.import_encoding_badge, ErrMsg.gedcom_encoding_wrong).to_have_attribute("data-gedcom-encoding", "utf-8")



@allure.title("GEDCOM: отмена на этапе превью сбрасывает в IDLE")
def test_cancel_during_preview_resets_to_idle(owner_page: Page, owner_user, tenant_client) -> None:
    """Cancel на PREVIEW возвращает в IDLE без записи persons."""
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
        should.be_equal(count_after, count_before, ErrMsg.person_count_wrong)


@allure.title("GEDCOM: отмена в диалоге подтверждения не импортирует данные")
def test_confirm_dialog_cancel_blocks_import(owner_page: Page, owner_user, tenant_client) -> None:
    """Отмена в confirmDialog оставляет в PREVIEW без записей в БД."""
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
        should.be_equal(count_after, count_before, ErrMsg.person_count_wrong)


@allure.title("GEDCOM: повторный импорт показывает счётчик пропущенных")
def test_done_shows_skipped_count_on_reimport(owner_page: Page, owner_user, tenant_client) -> None:
    """Повторный импорт показывает «Пропущено» в DONE summary."""
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
        should.contain(summary_text, t(GedcomImport.SKIPPED_LABEL), ErrMsg.gedcom_skipped_missing)


@allure.title("GEDCOM: после ошибки сервера Retry сбрасывает в IDLE")
def test_retry_after_error_resets_to_idle(owner_page: Page, owner_user) -> None:
    """Retry из ERROR сбрасывает state-machine в IDLE."""
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



@allure.title("GEDCOM: загрузка .txt файла отклоняется без отправки")
def test_rejects_non_ged_extension(owner_page: Page, owner_user) -> None:
    """Файл .txt отклоняется без отправки POST."""
    with step("подготовка: открыть вкладку импорта и установить слушатель"):
        owner = open_import_tab(owner_page)
        posted: list[str] = []
        owner_page.on("request", lambda req:
                      posted.append(req.url) if req.method == "POST"
                      and "/import-gedcom" in req.url else None)

    with step("действие: загрузить .txt файл"):
        owner.set_file_raw(name="notgedcom.txt", mime="text/plain", buffer=b"hello")

    with step("проверка: alertDialog появился и POST не отправлен"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(GedcomImport.FILE_EXTENSION_HINT)
        should.be_empty(posted, ErrMsg.gedcom_no_post_expected)
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")


@allure.title("GEDCOM: пустой .ged файл отклоняется с предупреждением")
def test_rejects_empty_file(owner_page: Page, owner_user) -> None:
    """Пустой .ged файл показывает alertDialog «пустой»."""
    with step("действие: загрузить пустой .ged файл"):
        owner = open_import_tab(owner_page)
        owner.set_file_raw(name="empty.ged", mime="application/octet-stream", buffer=b"")

    with step("проверка: alertDialog «пустой» и возврат в IDLE"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(t(GedcomImport.EMPTY_LABEL))
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")


@allure.title("GEDCOM: файл больше 10 МБ отклоняется на клиенте")
def test_rejects_oversize_file(owner_page: Page, owner_user) -> None:
    """Файл >10 MB отклоняется на клиенте."""
    with step("подготовка: создать payload >10 MB"):
        # `b"1 NOTE xx\n"` — ровно 10 байт, чтобы multiplier × 10 = bytes.
        big_payload = b"0 HEAD\n" + b"1 NOTE xx\n" * (11 * 1024 * 1024 // 10)
        should.greater(len(big_payload), 10 * 1024 * 1024, ErrMsg.payload_sanity)

    with step("действие: загрузить oversize файл"):
        owner = open_import_tab(owner_page)
        owner.set_file_raw(name="huge.ged", mime="application/octet-stream", buffer=big_payload)

    with step("проверка: alertDialog «слишком большой» и возврат в IDLE"):
        expect(owner.confirm_dialog, ErrMsg.dialog_not_visible).to_be_visible()
        expect(owner.confirm_dialog, ErrMsg.wrong_text_content).to_contain_text(t(GedcomImport.TOO_LARGE_LABEL))
        owner.confirm_dialog_ok.click()
        owner.expect_import_state("IDLE")



@allure.title("GEDCOM: ошибка 400 от бэкенда показывает detail в UI")
def test_backend_400_shows_friendly_error(owner_page: Page, owner_user) -> None:
    """Backend 400 с detail отображается как inline ERROR."""
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
def test_network_error_shows_friendly_message(owner_page: Page, owner_user) -> None:
    """Network abort показывает ERROR с понятным сообщением."""
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
