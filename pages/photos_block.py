"""POM for the photos-block inside the person editor.

Selectors from js/components/photos-block.js. The block lets an editor
upload person photos and remove them from the grid.

Layout:
    .photos-block
      #photoAddBtn       <- label[for=photoFileInput] — visible "Add" button
      #photoFileInput    <- input[type=file] — hidden, accepts images
      #photoUploadZone   <- drag-drop zone
      #photoGrid         <- thumbnail grid
        .photo-thumb[data-photo-index][data-photo-id]
          .photo-remove  <- delete cross per thumb
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step
from test_data.media.jpeg import MIN_JPEG_BYTES


class PhotosBlock:
    """Drives the photos-block: upload, count, remove thumbnails."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def container(self) -> Locator:
        """no semantic: photo container, no ARIA"""
        return self.page.locator('[data-testid="photos-block"]')

    @property
    def add_btn(self) -> Locator:
        """no semantic: upload widget, no role"""
        return self.page.locator("#photoAddBtn")

    @property
    def file_input(self) -> Locator:
        """no semantic: hidden file input, no label"""
        return self.page.locator("#photoFileInput")

    @property
    def grid(self) -> Locator:
        """no semantic: photo container, no ARIA"""
        return self.page.locator("#photoGrid")

    @property
    def thumbs(self) -> Locator:
        """no semantic: photo container, no ARIA"""
        return self.grid.locator('[data-testid="photo-thumb"]')

    def thumb_count(self) -> int:
        """Return the current number of photo thumbnails."""
        return self.thumbs.count()

    def remove_last_thumb(self) -> Locator:
        """Return the `.photo-remove` locator on the last thumb (caller
        should click it inside an expect_response context)."""
        return self.thumbs.last.locator('[data-testid="photo-remove"]')  # no semantic: upload widget, no role

    def remove_last(self) -> None:
        """Click the remove button on the last thumbnail."""
        with step("действие: удалить последнее фото"):
            self.remove_last_thumb().click()

    def expect_thumb_count(self, n: int) -> None:
        """Assert exactly n thumbnails are present in the grid."""
        with step("проверка: количество фото"):
            expect(self.thumbs).to_have_count(n)

    def add_btn_for_attr(self) -> str | None:
        """Return the `for` attribute of the add-photo label."""
        return self.add_btn.get_attribute("for")

    def file_input_accept(self) -> str | None:
        """Return the `accept` attribute of the file input."""
        return self.file_input.get_attribute("accept")

    def upload_test_jpeg(self, *, name: str = "test.jpg") -> None:
        """Upload a minimal test JPEG via the file input."""
        with step("действие: загрузить фото"):
            self.file_input.set_input_files(
                files=[{"name": name, "mimeType": "image/jpeg", "buffer": MIN_JPEG_BYTES}]  # type: ignore[arg-type]
            )
