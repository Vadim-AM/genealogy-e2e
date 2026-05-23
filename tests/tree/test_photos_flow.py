"""TC-08.01, TC-08.02, TC-08.11 — Photos UI flow в person-editor.

Editor содержит блок `.photos-block` (рендерится `js/components/photos-block.js`):
- `#photoFileInput` (input type=file, accept=image/*, visually-hidden) — file chooser
- `#photoAddBtn` (label[for=photoFileInput]) — кнопка «Добавить фото»
- `#photoUploadZone` — drag-drop зона
- `#photoGrid` — рендер списка существующих фото; каждый thumb — `.photo-thumb`
  с `data-photo-index`/`data-photo-id` и крестик `.photo-remove`

Backend: POST /api/admin/upload-photo (multipart) → возвращает path,
который JS добавляет в `currentPhotos[]` и перерендеривает grid. Hard-delete:
PATCH /api/admin/people/{id} с `{photos: <без удалённой>}`.

Backend-уровень покрыт `genealogy/backend/tests/test_photo_upload.py`
(MIME валидация, EXIF orientation, storage cap, permissions). Здесь —
UI flow: input file → thumb появился, крестик → thumb убран.

Note: admin/people.js использует другой `renderPhotoBlock` с обёрткой
`#photoManager` — это legacy /admin путь, не покрывается этим файлом.
"""

from __future__ import annotations

import re

import allure
from playwright.sync_api import Page, expect

from tests.helpers.tree.photos import upload_jpeg
from tests.messages import Buttons, TestData, t
from tests.pages.photos_block import PhotosBlock
from tests.pages.profile_panel import open_editor_for


@allure.title("Блок фото отображается в редакторе с кнопкой добавления")
def test_photos_block_renders_inside_editor(owner_page: Page):
    """TC-08.01 (precondition): `.photos-block` есть в editor'е,
    содержит file-input + label-кнопку «Добавить фото» + drag-drop zone.
    """
    open_editor_for(owner_page)
    photos = PhotosBlock(owner_page)

    expect(photos.container).to_be_visible()
    expect(photos.add_btn).to_be_visible()
    expect(photos.add_btn).to_contain_text(t(Buttons.ADD))
    assert photos.add_btn.get_attribute("for") == "photoFileInput", (
        "label#photoAddBtn должен иметь for=photoFileInput для нативного "
        "click-to-open-file-chooser flow"
    )

    assert photos.file_input.count() == 1, "ожидаем ровно один #photoFileInput"
    accept = photos.file_input.get_attribute("accept")
    assert accept and "image" in accept, (
        f"#photoFileInput accept должен фильтровать images; got accept={accept!r}"
    )


@allure.title("Загрузка фото добавляет миниатюру в сетку")
def test_photo_upload_via_file_input_appends_thumb_to_grid(owner_page: Page):
    """TC-08.02: set_input_files с JPEG → POST /api/admin/upload-photo
    → backend отвечает path → JS добавляет в #photoGrid новый
    `.photo-thumb`. Перед upload — `<span>Нет фото</span>` placeholder
    или пустой grid (в зависимости от seed).
    """
    open_editor_for(owner_page)
    photos = PhotosBlock(owner_page)
    initial_thumbs = photos.thumb_count()

    # Wait for upload XHR fulfillment перед thumb-проверкой.
    with owner_page.expect_response(
        lambda r: "/api/admin/upload-photo" in r.url and r.status == 200
    ):
        upload_jpeg(owner_page)

    # После успешного upload JS перерендеривает grid — thumb count
    # вырастает на 1.
    photos.expect_thumb_count(initial_thumbs + 1)


@allure.title("Удаление фото убирает миниатюру из сетки")
def test_photo_remove_button_drops_thumb_from_grid(owner_page: Page):
    """TC-08.11: после upload click `.photo-remove` → PATCH
    /api/admin/people/{id} (photos без удалённой) → JS перерендеривает
    grid — thumb count уменьшается обратно.
    """
    open_editor_for(owner_page)
    photos = PhotosBlock(owner_page)
    initial = photos.thumb_count()

    # Сначала добавим фото, чтобы было что удалять. expect_response даёт
    # backend OK, но render — async; ждём через expect.to_have_count.
    with owner_page.expect_response(
        lambda r: "/api/admin/upload-photo" in r.url and r.status == 200
    ):
        upload_jpeg(owner_page)
    photos.expect_thumb_count(initial + 1)
    after_upload = initial + 1

    # Click крестик последнего thumb — JS делает PATCH /api/people/{id}
    # (см. photos-block.js:289). На backend это hard-delete файла.
    with owner_page.expect_response(
        lambda r: re.search(r"/api/people/[^/]+$", r.url) and r.request.method == "PATCH"
    ):
        photos.remove_last_thumb().click()

    photos.expect_thumb_count(after_upload - 1)
