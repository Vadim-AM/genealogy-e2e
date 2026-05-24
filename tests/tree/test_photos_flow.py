"""TC-08: Photos UI flow — upload, thumb, remove в person-editor."""

from __future__ import annotations

import re
from http import HTTPStatus

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.step import step
from pages.photos_block import PhotosBlock
from pages.profile_panel import open_editor_for
from src.texts import Buttons, ErrMsg, t


@allure.title("Блок фото отображается в редакторе с кнопкой добавления")
def test_photos_block_renders_inside_editor(owner_page: Page) -> None:
    """Photos-block содержит file-input и кнопку добавления."""
    with step("действие: открытие редактора"):
        open_editor_for(owner_page)
        photos = PhotosBlock(owner_page)

    with step("проверка: кнопка добавления и file-input видны"):
        expect(photos.container, ErrMsg.photo_not_visible).to_be_visible()
        expect(photos.add_btn, ErrMsg.button_not_visible).to_be_visible()
        expect(photos.add_btn, ErrMsg.wrong_text_content).to_contain_text(t(Buttons.ADD))
        should.be_equal(photos.add_btn_for_attr(), "photoFileInput", ErrMsg.photo_label_for_wrong)

        should.be_equal(photos.file_input.count(), 1, ErrMsg.photo_input_count_wrong)
        accept = photos.file_input_accept()
        should.be_true(accept and "image" in accept, ErrMsg.photo_accept_wrong)


@allure.title("Загрузка фото добавляет миниатюру в сетку")
def test_photo_upload_via_file_input_appends_thumb_to_grid(owner_page: Page) -> None:
    """Upload JPEG через file-input добавляет thumb в grid."""
    with step("подготовка: открытие редактора и подсчёт миниатюр"):
        open_editor_for(owner_page)
        photos = PhotosBlock(owner_page)
        initial_thumbs = photos.thumb_count()

    with (
        step("действие: загрузка JPEG"),
        owner_page.expect_response(lambda r: routes.UPLOAD_PHOTO in r.url and r.status == HTTPStatus.OK),
    ):
        photos.upload_test_jpeg()

    with step("проверка: миниатюра добавлена в сетку"):
        photos.expect_thumb_count(initial_thumbs + 1)


@allure.title("Удаление фото убирает миниатюру из сетки")
def test_photo_remove_button_drops_thumb_from_grid(owner_page: Page) -> None:
    """Удаление thumb через .photo-remove уменьшает count обратно."""
    with step("подготовка: открыть редактор и загрузить фото"):
        open_editor_for(owner_page)
        photos = PhotosBlock(owner_page)
        initial = photos.thumb_count()

        with owner_page.expect_response(lambda r: routes.UPLOAD_PHOTO in r.url and r.status == HTTPStatus.OK):
            photos.upload_test_jpeg()
        photos.expect_thumb_count(initial + 1)
        after_upload = initial + 1

    with (
        step("действие: удалить последнюю миниатюру"),
        owner_page.expect_response(
            lambda r: bool(re.search(rf"{routes.PEOPLE}/[^/]+$", r.url) and r.request.method == "PATCH")
        ),
    ):
        photos.remove_last()

    with step("проверка: миниатюра убрана из сетки"):
        photos.expect_thumb_count(after_upload - 1)
