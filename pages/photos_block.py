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


class PhotosBlock:
    """Drives the photos-block: upload, count, remove thumbnails."""

    def __init__(self, page: Page):
        self.page = page
        self.container = page.locator('[data-testid="photos-block"]')  # no semantic: photo container, no ARIA
        self.add_btn = page.locator("#photoAddBtn")  # no semantic: upload widget, no role
        self.file_input = page.locator("#photoFileInput")  # no semantic: hidden file input, no label
        self.grid = page.locator("#photoGrid")  # no semantic: photo container, no ARIA
        self.thumbs = self.grid.locator('[data-testid="photo-thumb"]')  # no semantic: photo container, no ARIA

    def thumb_count(self) -> int:
        """Return the current number of photo thumbnails."""
        return self.thumbs.count()

    def remove_last_thumb(self) -> Locator:
        """Return the `.photo-remove` locator on the last thumb (caller
        should click it inside an expect_response context)."""
        return self.thumbs.last.locator('[data-testid="photo-remove"]')  # no semantic: upload widget, no role

    def expect_thumb_count(self, n: int) -> None:
        """Assert exactly n thumbnails are present in the grid."""
        expect(self.thumbs).to_have_count(n)

    def add_btn_for_attr(self) -> str | None:
        """Return the `for` attribute of the add-photo label."""
        return self.add_btn.get_attribute("for")

    def file_input_accept(self) -> str | None:
        """Return the `accept` attribute of the file input."""
        return self.file_input.get_attribute("accept")
