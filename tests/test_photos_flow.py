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

from playwright.sync_api import Page, expect

from tests.messages import TestData
from tests.pages.person_editor import PersonEditor
from tests.pages.profile_panel import ProfilePanel


# Минимальный валидный JPEG 1×1 (~640 байт). Достаточно для прохождения
# `Image.open()` Pillow-валидации в backend (admin_modules/photos.py).
_MIN_JPEG_BYTES = bytes.fromhex(
    "FFD8FFE000104A46494600010100000100010000FFDB004300080606070605080707"
    "070909080A0C140D0C0B0B0C1912130F141D1A1F1E1D1A1C1C20242E2720222C231C"
    "1C2837292C30313434341F27393D38323C2E333432FFC0000B0800010001010111"
    "00FFC4001F0000010501010101010100000000000000000102030405060708090A"
    "0BFFC400B5100002010303020403050504040000017D01020300041105122131410"
    "613516107227114328191A1082342B1C11552D1F02433627282090A161718191A2"
    "5262728292A3435363738393A434445464748494A535455565758595A636465666"
    "768696A737475767778797A838485868788898A92939495969798999AA2A3A4A5A"
    "6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE1E"
    "2E3E4E5E6E7E8E9EAF1F2F3F4F5F6F7F8F9FAFFDA0008010100003F00FBFC11FFD9"
)


def _open_editor(owner_page: Page, person_id: str = TestData.DEMO_PERSON_ID) -> PersonEditor:
    owner_page.goto(f"/#/p/{person_id}")
    owner_page.wait_for_load_state("networkidle")
    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.open_editor()
    editor = PersonEditor(owner_page)
    editor.expect_visible()
    return editor


def _upload_jpeg(page: Page, *, name: str = "test.jpg") -> None:
    """Отдать минимальный JPEG в `#photoFileInput`. Playwright обходит
    file-chooser dialog через CDP — input может быть hidden.
    """
    page.locator("#photoFileInput").set_input_files(
        files=[{"name": name, "mimeType": "image/jpeg", "buffer": _MIN_JPEG_BYTES}]
    )


def test_photos_block_renders_inside_editor(owner_page: Page):
    """TC-08.01 (precondition): `.photos-block` есть в editor'е,
    содержит file-input + label-кнопку «Добавить фото» + drag-drop zone.
    """
    _open_editor(owner_page)

    expect(owner_page.locator(".photos-block")).to_be_visible()
    # `#photoAddBtn` это `<label for="photoFileInput">` — visible как label.
    add_btn = owner_page.locator("#photoAddBtn")
    expect(add_btn).to_be_visible()
    expect(add_btn).to_contain_text("Добавить")
    # label должен указывать на правильный input.
    assert add_btn.get_attribute("for") == "photoFileInput", (
        "label#photoAddBtn должен иметь for=photoFileInput для нативного "
        "click-to-open-file-chooser flow"
    )

    # Hidden input обязан существовать (set_input_files работает через CDP
    # независимо от visually-hidden CSS).
    file_input = owner_page.locator("#photoFileInput")
    assert file_input.count() == 1, "ожидаем ровно один #photoFileInput"
    accept = file_input.get_attribute("accept")
    assert accept and "image" in accept, (
        f"#photoFileInput accept должен фильтровать images; got accept={accept!r}"
    )


def test_photo_upload_via_file_input_appends_thumb_to_grid(owner_page: Page):
    """TC-08.02: set_input_files с JPEG → POST /api/admin/upload-photo
    → backend отвечает path → JS добавляет в #photoGrid новый
    `.photo-thumb`. Перед upload — `<span>Нет фото</span>` placeholder
    или пустой grid (в зависимости от seed).
    """
    _open_editor(owner_page)
    grid = owner_page.locator("#photoGrid")
    initial_thumbs = grid.locator(".photo-thumb").count()

    # Wait for upload XHR fulfillment перед thumb-проверкой.
    with owner_page.expect_response(
        lambda r: "/api/admin/upload-photo" in r.url and r.status == 200
    ):
        _upload_jpeg(owner_page)

    # После успешного upload JS перерендеривает grid — thumb count
    # вырастает на 1.
    expect(grid.locator(".photo-thumb")).to_have_count(initial_thumbs + 1)


def test_photo_remove_button_drops_thumb_from_grid(owner_page: Page):
    """TC-08.11: после upload click `.photo-remove` → PATCH
    /api/admin/people/{id} (photos без удалённой) → JS перерендеривает
    grid — thumb count уменьшается обратно.
    """
    _open_editor(owner_page)
    grid = owner_page.locator("#photoGrid")
    initial = grid.locator(".photo-thumb").count()

    # Сначала добавим фото, чтобы было что удалять. expect_response даёт
    # backend OK, но render — async; ждём через expect.to_have_count.
    with owner_page.expect_response(
        lambda r: "/api/admin/upload-photo" in r.url and r.status == 200
    ):
        _upload_jpeg(owner_page)
    expect(grid.locator(".photo-thumb")).to_have_count(initial + 1)
    after_upload = initial + 1

    # Click крестик последнего thumb — JS делает PATCH /api/people/{id}
    # (см. photos-block.js:289). На backend это hard-delete файла.
    last_remove = grid.locator(".photo-thumb").last.locator(".photo-remove")
    with owner_page.expect_response(
        lambda r: re.search(r"/api/people/[^/]+$", r.url) and r.request.method == "PATCH"
    ):
        last_remove.click()

    expect(grid.locator(".photo-thumb")).to_have_count(after_upload - 1)
