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
        self.container = page.locator('[data-testid="photos-block"]')
        self.add_btn = page.locator("#photoAddBtn")
        self.file_input = page.locator("#photoFileInput")
        self.grid = page.locator("#photoGrid")
        self.thumbs = self.grid.locator('[data-testid="photo-thumb"]')

    def thumb_count(self) -> int:
        return self.thumbs.count()

    def remove_last_thumb(self) -> Locator:
        """Return the `.photo-remove` locator on the last thumb (caller
        should click it inside an expect_response context)."""
        return self.thumbs.last.locator('[data-testid="photo-remove"]')

    def expect_thumb_count(self, n: int) -> None:
        expect(self.thumbs).to_have_count(n)
